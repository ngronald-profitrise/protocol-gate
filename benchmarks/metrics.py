"""Prometheus metric definitions for the harness and benchmarks.

All metrics are defined once here and imported everywhere so label sets stay
consistent. A dedicated :class:`CollectorRegistry` is exposed so the benchmark
runner can push a clean snapshot without global-registry pollution during tests.
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
)

REGISTRY = CollectorRegistry()

# Latency buckets tuned for sub-millisecond gate steps up to slow LLM calls.
_STEP_BUCKETS = (
    0.0001,
    0.0005,
    0.001,
    0.005,
    0.01,
    0.05,
    0.1,
    0.5,
    1.0,
    5.0,
)

proposals_total = Counter(
    "protocol_gate_proposals_total",
    "Total proposals submitted through an arm.",
    ["arm", "scenario", "result"],
    registry=REGISTRY,
)

rejection_total = Counter(
    "protocol_gate_rejection_total",
    "Proposals rejected by the gate, by reason code.",
    ["arm", "scenario", "reason_code"],
    registry=REGISTRY,
)

unauthorized_effects_total = Counter(
    "protocol_gate_unauthorized_effects_total",
    "Effects executed without a valid authorized transition (should be 0 gated).",
    ["arm", "scenario"],
    registry=REGISTRY,
)

state_violations_total = Counter(
    "protocol_gate_state_violations_total",
    "State-invariant violations observed after an arm executed.",
    ["arm", "scenario"],
    registry=REGISTRY,
)

replay_success_total = Counter(
    "protocol_gate_replay_success_total",
    "Replay attacks that succeeded in causing an effect.",
    ["arm"],
    registry=REGISTRY,
)

injection_success_total = Counter(
    "protocol_gate_injection_success_total",
    "Prompt-injection attempts that succeeded in causing an effect.",
    ["arm"],
    registry=REGISTRY,
)

latency_seconds = Histogram(
    "protocol_gate_latency_seconds",
    "Per-step latency of the 12-step PAVSCE-A pipeline.",
    ["arm", "step"],
    buckets=_STEP_BUCKETS,
    registry=REGISTRY,
)

audit_completeness_ratio = Gauge(
    "protocol_gate_audit_completeness_ratio",
    "Fraction of decisions that produced a durable audit record (target 1.0).",
    ["arm"],
    registry=REGISTRY,
)

token_scrub_actions_total = Counter(
    "protocol_gate_token_scrub_actions_total",
    "Scrubbing actions taken, by action type.",
    ["action_type"],
    registry=REGISTRY,
)

ollama_tokens_per_second = Gauge(
    "ollama_tokens_per_second",
    "Observed model generation throughput.",
    ["model", "arm"],
    registry=REGISTRY,
)

ollama_time_to_first_token_seconds = Histogram(
    "ollama_time_to_first_token_seconds",
    "Model time-to-first-token latency.",
    ["model", "arm"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
    registry=REGISTRY,
)


def step_timer(arm: str):
    """Return a ``(step, seconds)`` callback bound to an arm for the kernel."""

    def _record(step: str, seconds: float) -> None:
        latency_seconds.labels(arm=arm, step=step).observe(seconds)

    return _record
