"""The EXPERIMENT arm: the full Protocol Gate harness.

Model output is scrubbed, then evaluated by the kernel. Effects only occur on an
:class:`AcceptedTransition`. Replay is exercised by resubmitting the identical
scrubbed proposal and confirming the second attempt is rejected.
"""

from __future__ import annotations

from typing import Any, Callable

from experiments.scenarios.base import Scenario, ScenarioResult, World
from protocol_gate import AcceptedTransition, ProtocolGate, scrub
from specs import load_default_spec

StepTimer = Callable[[str, float], None]


def run_experiment(
    scenario: Scenario, world: World, *, step_timer: StepTimer | None = None
) -> ScenarioResult:
    """Execute a scenario through the full gate."""

    spec = load_default_spec()
    gate = ProtocolGate(
        spec=spec,
        state_store=world.store,
        authority=world.authority,
        evidence=world.evidence,
        effects=world.effects,
        step_timer=step_timer,
    )

    text = scenario.raw_model_output()
    scrub_result = scrub(text, source="llm")
    result = gate.evaluate(scrub_result.proposal, scrub_actions=scrub_result.actions)
    accepted = isinstance(result, AcceptedTransition)

    detail: dict[str, Any] = {
        "scrub_actions": scrub_result.actions,
        "injection_detected": scrub_result.injection_detected,
        "decision": type(result).__name__,
    }
    if not accepted:
        detail["reason_code"] = result.reason_code.value  # type: ignore[union-attr]

    effects_before = len(world.effects.log)

    # Replay: resubmit the identical proposal; must be rejected (fail-closed).
    replay_effected = False
    if getattr(scenario, "replay", False):
        replay_scrub = scrub(text, source="llm")
        replay_result = gate.evaluate(
            replay_scrub.proposal, scrub_actions=replay_scrub.actions
        )
        replay_accepted = isinstance(replay_result, AcceptedTransition)
        replay_effected = len(world.effects.log) > effects_before and replay_accepted
        detail["replay_decision"] = type(replay_result).__name__
    detail["replay_effected"] = replay_effected

    scored = scenario.score(
        ScenarioResult(
            accepted=accepted,
            effects_executed=len(world.effects.log),
            security_failure=False,
            detail=detail,
        )
    )
    return scored
