# ADR-0007: Control-vs-experiment A/B harness

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** Ronald

## Context and problem statement

Claiming a security benefit is not enough; we should *demonstrate* it. We need a reproducible way to show that identical adversarial inputs succeed against an ungated baseline but fail against the gated system.

## Decision drivers

- Reproducible, quantitative evidence of the security delta.
- Same scenarios run through both arms.
- Results feed metrics/dashboards and experiment tracking.

## Considered options

1. **Assert the benefit in prose/tests only.**
2. **A/B harness** with a genuinely ungated control arm and a gated experiment arm, sharing one scenario set.

## Decision outcome

Chosen option: **"A/B harness"** (`experiments/control/`, `experiments/experiment/`, `experiments/runner.py`, `experiments/scenarios/*`). Adversarial scenarios (replay, prompt injection, authority escalation, state confusion, malformed proposal) plus a happy path run through both arms. The control executes effects directly from proposals (untrusted-controller anti-pattern); the experiment routes everything through the gate. Metrics (replay/injection successes, unauthorized effects, state violations) are recorded per arm and surfaced in the "Control vs Experiment" dashboard and MLflow.

### Consequences

- Good: the security benefit is measured, not asserted; the control shows >0 successes, the experiment shows 0.
- Good: new attacks are added as scenarios and immediately tested against both arms.
- Bad: the control must be kept genuinely ungated to remain a fair baseline (enforced by review, per AGENTS.md).

## Pros and cons of the options

### Prose/tests only
- Bad: no quantitative, reproducible evidence; easy to overclaim.
