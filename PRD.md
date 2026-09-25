# Product Requirements Document — Protocol Gate

- **Status:** Accepted
- **Owner:** Ronald (@ngronald-profitrise)
- **Last updated:** 2026-09-25
- **Related:** [TRD.md](TRD.md) · [DESIGN.md](DESIGN.md) · [docs/adr/](docs/adr/)

---

## 1. Overview

Protocol Gate is a harness for building LLM‑driven agents that can act on the world **without trusting the model with authority**. It reframes the language model as an *untrusted proposer* whose output is a *request*, not a command. A deterministic, formally specified gate — the 12‑step **PAVSCE‑A** pipeline — is the single component that decides whether any proposed action is executed.

The product is aimed at engineers building agentic systems who need auditable, injection‑resistant, replay‑resistant control over effectful actions.

## 2. Problem statement

Modern agent frameworks route model output more or less directly into effectful tool calls. This makes the model a trusted controller and exposes the system to:

- **Prompt injection** — untrusted content instructs the model to take unintended actions.
- **Authority escalation** — the model emits control fields (e.g. `"authorized": true`) that widen its own permissions.
- **Replay** — stale or duplicated proposals cause effects to fire twice.
- **State confusion** — actions are accepted from illegal states.
- **Non‑auditability** — decisions are implicit, so there is no durable record of *why* an action happened.

There is no widely adopted, formally grounded pattern that makes "the model can only propose; a deterministic authority decides" the *default*.

## 3. Goals & non‑goals

### Goals
- Make **fail‑closed** the default behavior for all agent actions.
- Provide a **deterministic, total** decision function with a complete rejection taxonomy.
- Produce a **durable audit record for every decision** (accepted or rejected).
- Ship **formal verification** (TLA⁺) and **property‑based tests** for the core guarantee.
- Empirically **demonstrate** the security benefit via a control‑vs‑experiment A/B harness.
- Ship **production‑grade observability** (traces, metrics, logs, dashboards) out of the box.

### Non‑goals
- Replacing the LLM or improving its reasoning quality.
- Being a general workflow engine; the protocol spec is intentionally minimal and declarative.
- Providing a hardened multi‑tenant SaaS control plane (single‑node reference implementation).
- Guaranteeing model *helpfulness* — only that the model cannot exceed its authority.

## 4. Personas

- **Agent engineer (Ava)** — integrates the gate into an agent; needs a simple `evaluate()` contract and pluggable adapters.
- **Security reviewer (Sam)** — must be able to audit every decision and verify the guarantee formally.
- **SRE / operator (Omar)** — runs the stack; needs dashboards, traces, and alerts for unauthorized effects.
- **Researcher (Rae)** — studies the security delta; needs reproducible A/B experiments and metrics.

## 5. User stories

| ID | As a … | I want … | So that … |
|----|--------|----------|-----------|
| US-1 | agent engineer | to submit raw model output and get an accept/reject decision | I never wire model text into effects directly |
| US-2 | agent engineer | to declare protocol states, capabilities, and evidence in a spec file | I can change policy without touching kernel code |
| US-3 | security reviewer | a durable audit record for every decision | I can reconstruct exactly why any action happened |
| US-4 | security reviewer | a formal proof that no unauthorized effect can occur | I can trust the guarantee, not just the tests |
| US-5 | operator | Grafana dashboards showing unauthorized effects and audit completeness | I can detect drift or attack in real time |
| US-6 | operator | distributed traces of the 12 steps | I can see where latency or rejection happens |
| US-7 | researcher | a control‑vs‑experiment harness with adversarial scenarios | I can quantify the security benefit |
| US-8 | agent engineer | idempotent effects | retries and replays never double‑execute |
| US-9 | security reviewer | automatic scrubbing of injected instructions and control fields | model output can never smuggle authority |
| US-10 | operator | a one‑command local stack | I can evaluate the system quickly |

## 6. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | The gate SHALL expose a single `evaluate(proposal)` decision function that returns either `AcceptedTransition` or `RejectedProposal`. | P0 |
| FR-2 | The decision function SHALL be **total** — it never raises; unexpected errors become `INVARIANT_VIOLATION` rejections. | P0 |
| FR-3 | The gate SHALL scrub untrusted proposer output, removing injection patterns and forbidden control fields before parsing. | P0 |
| FR-4 | The gate SHALL authenticate the sender and reject unauthenticated or invalidly signed proposals. | P0 |
| FR-5 | The gate SHALL reject replayed, stale, or out‑of‑order proposals (nonce + sequence + freshness window). | P0 |
| FR-6 | The gate SHALL correlate each proposal to a known protocol instance and reject unknown instances (except valid initial actions). | P0 |
| FR-7 | The gate SHALL enforce **action‑scoped capabilities**; a token minted for one action cannot authorize another. | P0 |
| FR-8 | The gate SHALL validate the current state and reject illegal transitions per the declarative spec. | P0 |
| FR-9 | The gate SHALL validate required evidence/claims for each transition. | P0 |
| FR-10 | The gate SHALL check invariants and postconditions before committing. | P0 |
| FR-11 | The gate SHALL commit state idempotently and dispatch only permitted, idempotent effects. | P0 |
| FR-12 | The gate SHALL emit a durable audit record for **every** decision, accept or reject. | P0 |
| FR-13 | The protocol (states, transitions, capabilities, evidence, effects) SHALL be defined in a declarative YAML spec. | P0 |
| FR-14 | The system SHALL provide a control (ungated) and experiment (gated) arm running identical adversarial scenarios. | P1 |
| FR-15 | The system SHALL expose Prometheus metrics for proposals, rejections, unauthorized effects, audit completeness, and latency. | P1 |
| FR-16 | The system SHALL emit OpenTelemetry traces spanning the 12 steps. | P1 |
| FR-17 | The system SHALL provide provisioned Grafana dashboards and a Loki decision log. | P1 |
| FR-18 | The system SHALL provide pluggable adapters for state, authority, evidence, and effects (memory + postgres reference). | P1 |
| FR-19 | The system SHALL expose the gate over an HTTP API (FastAPI) with health endpoints. | P2 |
| FR-20 | The formal TLA⁺ specification SHALL be model‑checkable in CI‑friendly time. | P1 |

## 7. Non‑functional requirements

See [TRD.md §3](TRD.md) for the ISO/IEC 25010‑aligned NFR table. Summary of the headline targets:

| ID | Requirement |
|----|-------------|
| NFR-1 (Security) | Unauthorized effects in the gated arm MUST be exactly **0** across all scenarios. |
| NFR-2 (Reliability) | Audit completeness MUST be **1.0** (every decision recorded). |
| NFR-3 (Performance) | Median gate evaluation latency (excluding model inference) SHALL be < 5 ms on reference hardware. |
| NFR-4 (Maintainability) | Protocol changes SHALL require editing only the spec, not the kernel. |
| NFR-5 (Verifiability) | The core safety invariants SHALL be model‑checked by TLC in CI. |
| NFR-6 (Observability) | 100% of decisions SHALL be traceable and counted in metrics. |

## 8. Success metrics

- **Security delta:** control arm shows > 0 replay/injection/escalation successes; gated arm shows 0. (Demonstrated by `experiments/`.)
- **Audit completeness:** 1.0 in dashboards and property tests.
- **Test coverage of the guarantee:** property tests pass over ≥ 100 examples each; TLC finds no invariant violation.
- **Time‑to‑first‑value:** a new user can run the full stack and see the A/B result in < 15 minutes.

## 9. Assumptions & dependencies

- Ollama is available locally as the reference proposer (any model works; the gate is model‑agnostic).
- Docker + Docker Compose are available for the full stack.
- Python 3.12 for the implementation and tooling.
- The declarative spec is trusted configuration (authored by the operator, not the model).

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Operators mistake the gate for a model‑safety tool | Docs emphasize it constrains *authority*, not model quality. |
| Spec misconfiguration weakens guarantees | Spec loader validates structure; defaults are deny/fail‑closed. |
| Effect adapters with side effects are non‑idempotent | Adapter contract requires idempotency keys; reference adapter enforces it. |
| Formal model drifts from implementation | ADR‑0004 tracks the mapping; CI runs TLC and property tests together. |

## 11. Open questions

- Should the spec support hierarchical / nested protocols? (Deferred — see roadmap.)
- Should capability tokens be cryptographically verifiable (e.g. macaroons/JWT)? (Reference uses opaque tokens; see roadmap.)
