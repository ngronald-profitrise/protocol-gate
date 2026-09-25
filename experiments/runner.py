"""A/B experiment orchestrator.

Runs every scenario against both arms (control = raw LLM, experiment = gated),
records per-scenario outcomes, updates Prometheus metrics, and optionally logs an
MLflow run. Produces a plain-dict summary that the benchmark reporter serializes.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from benchmarks import metrics as M
from experiments.control.baseline import run_control
from experiments.experiment.gated import run_experiment
from experiments.scenarios import all_scenarios
from experiments.scenarios.base import Scenario, ScenarioResult


@dataclass
class ArmRecord:
    arm: str
    scenario: str
    accepted: bool
    effects_executed: int
    security_failure: bool
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentSummary:
    records: list[ArmRecord] = field(default_factory=list)

    def add(self, rec: ArmRecord) -> None:
        self.records.append(rec)

    def security_failures(self, arm: str) -> int:
        return sum(1 for r in self.records if r.arm == arm and r.security_failure)

    def to_dict(self) -> dict[str, Any]:
        arms = sorted({r.arm for r in self.records})
        return {
            "records": [asdict(r) for r in self.records],
            "summary": {
                arm: {
                    "security_failures": self.security_failures(arm),
                    "total_scenarios": sum(1 for r in self.records if r.arm == arm),
                    "accepted": sum(
                        1 for r in self.records if r.arm == arm and r.accepted
                    ),
                }
                for arm in arms
            },
        }


def _record_metrics(arm: str, scenario: Scenario, result: ScenarioResult) -> None:
    outcome = "accepted" if result.accepted else "rejected"
    M.proposals_total.labels(arm=arm, scenario=scenario.name, result=outcome).inc()
    if not result.accepted:
        reason = result.detail.get("reason_code", "control_blocked")
        M.rejection_total.labels(
            arm=arm, scenario=scenario.name, reason_code=str(reason)
        ).inc()
    if result.security_failure:
        M.state_violations_total.labels(arm=arm, scenario=scenario.name).inc()
        if scenario.name == "replay_attack":
            M.replay_success_total.labels(arm=arm).inc()
        if scenario.name == "prompt_injection":
            M.injection_success_total.labels(arm=arm).inc()
        if arm == "control":
            M.unauthorized_effects_total.labels(arm=arm, scenario=scenario.name).inc()
    for action in result.detail.get("scrub_actions", []):
        kind = str(action).split(":", 1)[0]
        M.token_scrub_actions_total.labels(action_type=kind).inc()


def run(*, arms: tuple[str, ...] = ("control", "experiment")) -> ExperimentSummary:
    summary = ExperimentSummary()
    for arm in arms:
        # Audit completeness is 1.0 for the gated arm (every decision audited)
        # and 0.0 for control (no audit trail at all).
        M.audit_completeness_ratio.labels(arm=arm).set(
            1.0 if arm == "experiment" else 0.0
        )
        for scenario in all_scenarios():
            world = scenario.build_world()
            scenario.seed(world)  # type: ignore[attr-defined]
            if arm == "control":
                result = run_control(scenario, world)
            else:
                result = run_experiment(
                    scenario, world, step_timer=M.step_timer("experiment")
                )
            _record_metrics(arm, scenario, result)
            summary.add(
                ArmRecord(
                    arm=arm,
                    scenario=scenario.name,
                    accepted=result.accepted,
                    effects_executed=result.effects_executed,
                    security_failure=result.security_failure,
                    detail=result.detail,
                )
            )
    return summary


def _maybe_log_mlflow(summary: ExperimentSummary) -> None:
    try:
        import mlflow  # type: ignore
    except ImportError:
        return
    try:
        with mlflow.start_run(run_name="protocol_gate_ab"):
            for arm, stats in summary.to_dict()["summary"].items():
                for key, value in stats.items():
                    mlflow.log_metric(f"{arm}_{key}", float(value))
    except Exception:  # noqa: BLE001 - MLflow server optional
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Protocol Gate A/B experiment")
    parser.add_argument("--output", default="-", help="output JSON path or '-'")
    parser.add_argument("--mlflow", action="store_true", help="log an MLflow run")
    args = parser.parse_args()

    summary = run()
    if args.mlflow:
        _maybe_log_mlflow(summary)
    payload = json.dumps(summary.to_dict(), indent=2)
    if args.output == "-":
        print(payload)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
