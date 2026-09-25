# ADR-0001: Deterministic gate as the sole authority (untrusted proposer)

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** Ronald

## Context and problem statement

LLM agents that take actions typically wire model output into effectful code. This makes a non-deterministic, promptable model the de facto controller, exposing the system to injection, hallucinated authority, and unauditable actions. We need an architecture where the model cannot cause effects on its own.

## Decision drivers

- The model must never gain authority.
- Decisions must be deterministic, reproducible, and auditable.
- The core must be verifiable (formally and via tests).
- Fail-closed by default.

## Considered options

1. **Trusted model + guardrail prompts.** Keep the model in control, add safety prompts.
2. **Deterministic gate as sole authority.** Demote the model to a proposer; a deterministic 12-step pipeline decides.
3. **Effect-layer authorization only.** Check authority just before executing effects.

## Decision outcome

Chosen option: **"Deterministic gate as sole authority"**. `ProtocolGate.evaluate()` is the only component that can produce an `AcceptedTransition`, and it is a **total, deterministic function** implementing the 12-step PAVSCE-A pipeline. Effects run only for accepted transitions. Every decision is audited.

### Consequences

- Good: the guarantee ("no effect without an accepted transition") is a single, testable, model-checkable property.
- Good: model output is data, not control flow.
- Bad: authors must model their domain as a protocol spec (states/transitions/capabilities/evidence).
- Bad: the gate adds latency (a few milliseconds) per action — negligible vs inference.

## Pros and cons of the options

### Trusted model + guardrail prompts
- Good: least code.
- Bad: not fail-closed; injectable; unauditable; unverifiable.

### Effect-layer authorization only
- Good: simple.
- Bad: authority checks happen too late to reject cheaply; no coherent state validation; weaker audit.
