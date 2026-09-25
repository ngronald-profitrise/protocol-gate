# Design — Protocol Gate

- **Status:** Accepted
- **Author:** Ronald (@ngronald-profitrise)
- **Reviewers:** —
- **Last updated:** 2026-09-25
- **Related:** [PRD.md](PRD.md) · [TRD.md](TRD.md) · [docs/adr/](docs/adr/)

## Context and scope

LLM agents that take real actions typically treat model output as trusted control flow. Protocol Gate exists to make the opposite the default: the model is an *untrusted proposer*, and a deterministic gate is the only authority that can cause effects. This document describes the design of that gate, its adapters, the harness that feeds it, and the observability and experiment tooling around it.

Scope: the single‑node reference implementation, its declarative spec, the 12‑step decision pipeline, pluggable adapters, the FastAPI surface, and the control‑vs‑experiment A/B framework. Out of scope: distributed consensus, multi‑tenant control planes, and model training.

## Goals and non‑goals

**Goals**
- A deterministic, total decision function with a complete rejection taxonomy.
- Durable audit for every decision.
- Formal verification of the safety invariants.
- Empirical demonstration of the security benefit.
- First‑class observability.

**Non‑goals**
- Improving model quality or helpfulness.
- Being a general workflow/BPM engine.
- Cryptographic capability tokens in the reference (opaque tokens suffice to demonstrate the design; see roadmap).

## The actual design

### Overview

The system has three trust zones:

1. **Untrusted** — the LLM (Ollama) and the raw text it emits.
2. **Boundary** — the *scrubber*, which converts untrusted text into a typed, sanitized `UntrustedProposal`.
3. **Trusted** — the deterministic kernel, adapters, state store, and audit log.

The kernel is a pure function of `(spec, current state, proposal)`; every side effect is delegated to an adapter. This keeps the decision logic deterministic and unit‑testable, and makes the TLA⁺ model a faithful abstraction of the code.

### The 12‑step PAVSCE‑A pipeline

`ProtocolGate.evaluate()` runs the following steps in order, short‑circuiting to a `RejectedProposal` at the first failure and instrumenting each step with a latency timer:

1. **Parse / normalize** — validate structure, known action, no unknown fields.
2. **Authenticate sender** — actor is known/trusted; signature present if required.
3. **Anti‑replay & freshness** — nonce unseen, timestamp within window.
4. **Correlate to instance** — map to an existing protocol instance (or a valid initial action).
5. **Validate authority** — action‑scoped capability token grants the action on the resource.
6. **Validate current state** — transition legal from the current status; sequence strictly increasing.
7. **Validate claims** — required evidence present and truthy.
8. **Compute transition** — deterministic target status + effects from the spec.
9. **Check invariants** — global invariants hold for the computed next state.
10. **Check postconditions** — transition‑specific postconditions hold.
11. **Commit state** — persist idempotently (idempotency key from action + instance + nonce).
12. **Dispatch effects + audit** — execute only permitted, idempotent effects; write the audit record.

The function is **total**: an outer try/except converts any unexpected error into an `INVARIANT_VIOLATION` rejection, preserving the fail‑closed contract even under bugs.

### Key components

- **`protocol_gate.models`** — typed domain model (`UntrustedProposal`, `ProtocolState`, `AcceptedTransition`, `RejectedProposal`, `RejectionCode`, `AuditRecord`).
- **`protocol_gate.scrubber`** — the trust boundary. Extracts JSON from fenced/raw model output, strips injection patterns and forbidden control fields, and records the scrub *actions* taken so they can be audited and counted.
- **`protocol_gate.state_machine`** — pure computation of transition legality/targets from the spec.
- **`protocol_gate.kernel`** — the 12‑step pipeline orchestrator.
- **`protocol_gate.audit`** — append‑only audit record construction (with a hash‑chainable field).
- **`adapters`** — `StateStore`, `AuthorityAdapter`, `EvidenceAdapter`, `EffectAdapter` protocols with in‑memory and PostgreSQL reference implementations.
- **`harness`** — Ollama client + proposer that turns a task into a model prompt, plus a runner that pipes proposals through the gate.
- **`specs`** — declarative YAML protocol + loader.
- **`api`** — FastAPI app exposing the gate and health/metrics endpoints, with OTel middleware.

### Data flow

```
model text ──▶ scrubber ──▶ UntrustedProposal ──▶ kernel.evaluate()
                                                      │
        ┌─────────────────────────────────────────────┤
        ▼                    ▼                          ▼
   StateStore          AuthorityAdapter           EffectAdapter
   (load/commit)       (authn + capability)       (idempotent effects)
        │                                              │
        └───────────────────▶ AuditRecord ◀───────────┘
```

### Adapter contracts

Adapters are `typing.Protocol` interfaces so any backend can be dropped in without touching the kernel (dependency inversion, see ADR‑0003):

- `StateStore.load(instance_id) -> ProtocolState | None` / `commit(state)`.
- `AuthorityAdapter.authenticate(proposal, max_age) -> AuthenticatedContext | None`, `has_capability(token, action, resource) -> bool`, nonce freshness/consumption.
- `EvidenceAdapter.verify(evidence, required) -> list[missing]`.
- `EffectAdapter.execute(effect, transition_id, idempotency_key, payload) -> receipt` (idempotent).

### Capability model

Capability tokens are **action‑scoped**. A token minted via `grant(actor, action, resource)` is `cap_{actor}_{action}`; `has_capability` verifies both that the owning actor holds the grant *and* that the token itself was minted for the requested action. This closes the escalation hole where a token issued for `OFFER` could otherwise authorize `COMPLETE` because the same actor happened to hold both grants (see ADR‑0003).

### Idempotency

Effects are keyed by `(effect, idempotency_key)`; the effect adapter caches receipts, so replays and retries return the cached receipt instead of re‑executing (ADR‑0005). Combined with nonce‑based replay rejection at step 3, this gives defense in depth.

## Alternatives considered

- **Trusted model with guardrail prompts.** Rejected: prompt‑based guardrails are not fail‑closed and can be injected around. The whole premise is to not trust the model.
- **Policy engine (e.g. OPA/Rego) as the gate.** Reasonable, but a general policy engine does not give a total, model‑checked *state machine* with a rejection taxonomy and audit contract out of the box. The declarative YAML spec plus a small kernel is easier to formally verify and to teach.
- **Embedding authority in the effect layer only.** Rejected: authority checks must precede state computation to reject early and cheaply, and to keep the audit record meaningful.
- **Cryptographic capabilities (macaroons/JWT) in the reference.** Deferred: opaque action‑scoped tokens are sufficient to demonstrate the guarantee; crypto tokens are a drop‑in adapter change (roadmap).

## Cross‑cutting concerns

### Security
Fail‑closed everywhere; scrubbing at the trust boundary; action‑scoped capabilities; replay/freshness enforcement; durable audit. See [SECURITY.md](SECURITY.md).

### Observability
Every step is timed and traced (OTel); every decision is counted (Prometheus) and logged (Loki). Three Grafana dashboards ship provisioned. The headline security metric — unauthorized effects — is a first‑class panel that must read 0 for the gated arm.

### Testing & verification
Unit + property (Hypothesis) + integration tests, plus TLA⁺/TLC model checking of the safety invariants. The property tests and the formal model target the *same* invariants, reducing model/implementation drift (ADR‑0004).

### Configuration
All runtime knobs via environment variables (`.env.example`); protocol policy via the YAML spec. No secrets in code.

## Rollout / how to adopt

1. Author a protocol spec (states, transitions, capabilities, evidence, effects).
2. Wire adapters for your state store, authority, evidence, and effects.
3. Feed model output through `scrub()` then `gate.evaluate()`.
4. Deploy with the provided stack for observability, or export metrics/traces to your own backends.

## Open questions

- Hierarchical/nested protocols.
- Cryptographically verifiable capabilities.
- Multi‑node audit log with tamper‑evidence (hash chain is stubbed for single node).
