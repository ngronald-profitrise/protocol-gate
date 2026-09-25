# Technical Requirements Document — Protocol Gate

- **Status:** Accepted
- **Owner:** Ronald (@ngronald-profitrise)
- **Last updated:** 2026-09-25
- **Related:** [PRD.md](PRD.md) · [DESIGN.md](DESIGN.md) · [docs/adr/](docs/adr/)

---

## 1. Purpose & scope

This document translates the [PRD](PRD.md) into concrete technical requirements, architecture constraints, non‑functional targets, and a **traceability matrix** linking requirements to design decisions, code, and tests. Scope is the reference single‑node implementation and its observability/experiment tooling.

## 2. Architecture constraints

| ID | Constraint |
|----|-----------|
| TC-1 | The kernel MUST be a pure, deterministic module with no I/O; all I/O is behind adapter interfaces. |
| TC-2 | `ProtocolGate.evaluate()` MUST be a total function (never raises). |
| TC-3 | All authority/state/evidence/effect access MUST go through typed adapter protocols (dependency inversion). |
| TC-4 | The protocol MUST be data‑driven from a declarative YAML spec; kernel code MUST NOT hardcode transitions. |
| TC-5 | Untrusted model output MUST be scrubbed and parsed into a typed `UntrustedProposal` before any authority logic runs. |
| TC-6 | Effects MUST be idempotent, keyed by `(effect, idempotency_key)`. |
| TC-7 | Observability MUST use OpenTelemetry (traces) + Prometheus (metrics) + structured logs (Loki), with no vendor lock‑in. |
| TC-8 | Python 3.12; typed with mypy; linted with ruff; formatted with black. |
| TC-9 | The formal spec MUST be model‑checkable by TLC within a few minutes on a laptop. |

## 3. Non‑functional requirements (ISO/IEC 25010)

| ISO 25010 characteristic | ID | Requirement | Verification |
|--------------------------|----|-------------|--------------|
| Functional suitability | NFR-1 | 0 unauthorized effects in the gated arm across all scenarios | `experiments/`, property tests, dashboards |
| Reliability | NFR-2 | Audit completeness = 1.0 (every decision recorded) | `tests/property/test_audit_completeness.py` |
| Reliability | NFR-7 | Gate is fail‑closed: unknown/error → rejection | `tests/property/test_fail_closed.py`, TLC |
| Performance efficiency | NFR-3 | Median in‑process gate latency < 5 ms (excl. inference) | `benchmarks/` |
| Maintainability | NFR-4 | Protocol changes require only spec edits | code review, `specs/loader.py` |
| Security | NFR-8 | Action‑scoped capabilities; no privilege widening | `tests/property/test_authorization.py` |
| Security | NFR-9 | Injection/control‑field scrubbing on all model output | `tests/unit/test_scrubber.py` |
| Portability | NFR-10 | Pluggable adapters (memory + postgres) | `adapters/`, integration tests |
| Compatibility | NFR-6 | 100% of decisions emit metrics + traces | `benchmarks/metrics.py`, OTel spans |
| Verifiability | NFR-5 | Safety invariants model‑checked by TLC | `proofs/`, CI |

## 4. Traceability matrix

Links **functional requirements** → **architecture decisions (ADR)** → **implementation** → **tests**.

| FR | Description | ADR | Implementation | Tests |
|----|-------------|-----|----------------|-------|
| FR-1 | Single `evaluate()` decision fn | ADR-0001 | `src/protocol_gate/kernel.py::ProtocolGate.evaluate` | `tests/unit/test_kernel.py` |
| FR-2 | Total function (never raises) | ADR-0001 | `kernel.py::evaluate` (try/except → `INVARIANT_VIOLATION`) | `tests/unit/test_kernel.py::test_kernel_never_raises_on_garbage`, `tests/property/test_fail_closed.py` |
| FR-3 | Scrub injection + control fields | ADR-0002 | `src/protocol_gate/scrubber.py` | `tests/unit/test_scrubber.py` |
| FR-4 | Authenticate sender | ADR-0001 | `adapters/memory.py::authenticate` | `tests/unit/test_kernel.py::test_unauthenticated_sender_rejected` |
| FR-5 | Anti‑replay / freshness / order | ADR-0001 | `kernel.py` steps 3 & 6, `adapters/memory.py` nonce store | `tests/integration/test_rejection_taxonomy.py::test_replay_detected`, `::test_out_of_order_sequence` |
| FR-6 | Correlate to instance | ADR-0001 | `kernel.py` step 4 | `tests/integration/test_rejection_taxonomy.py` |
| FR-7 | Action‑scoped capabilities | ADR-0003 | `adapters/memory.py::has_capability` | `tests/property/test_authorization.py`, `tests/unit/test_kernel.py::test_insufficient_capability_rejected` |
| FR-8 | Validate current state | ADR-0001 | `src/protocol_gate/state_machine.py`, `kernel.py` step 6 | `tests/unit/test_state_machine.py`, `tests/integration/test_rejection_taxonomy.py::test_invalid_current_state` |
| FR-9 | Validate evidence | ADR-0001 | `adapters/memory.py::verify`, `kernel.py` step 7 | `tests/integration/test_rejection_taxonomy.py::test_insufficient_evidence` |
| FR-10 | Invariants + postconditions | ADR-0001 | `kernel.py` steps 9–10 | `tests/property/test_fail_closed.py` |
| FR-11 | Idempotent commit + effects | ADR-0005 | `adapters/memory.py::InMemoryEffectAdapter.execute` | `tests/property/test_idempotency.py`, `tests/integration/test_happy_path.py::test_effects_are_idempotent_on_replayed_transition` |
| FR-12 | Audit every decision | ADR-0001 | `src/protocol_gate/audit.py` | `tests/unit/test_audit.py`, `tests/property/test_audit_completeness.py` |
| FR-13 | Declarative spec | ADR-0006 | `src/specs/task_protocol.yaml`, `src/specs/loader.py` | `tests/unit/test_kernel.py` (uses loaded spec) |
| FR-14 | Control vs experiment arms | ADR-0007 | `experiments/control/`, `experiments/experiment/`, `experiments/runner.py` | `experiments/scenarios/*` |
| FR-15 | Prometheus metrics | ADR-0008 | `benchmarks/metrics.py` | `benchmarks/runner.py` |
| FR-16 | OpenTelemetry traces | ADR-0008 | `src/api/middleware.py`, `kernel.py` step timers | manual/stack |
| FR-17 | Grafana dashboards + Loki | ADR-0008 | `infra/grafana/dashboards/*.json`, `infra/loki/` | JSON schema validation |
| FR-18 | Pluggable adapters | ADR-0003 | `src/adapters/base.py`, `memory.py`, `postgres.py` | `tests/*` (memory) |
| FR-19 | HTTP API | ADR-0001 | `src/api/` | `tests/integration/*` (via TestClient‑ready app) |
| FR-20 | Model‑checkable TLA⁺ | ADR-0004 | `proofs/ProtocolGate.tla`, `.cfg` | `proofs/README.md`, CI `make proofs` |

## 5. Data model (summary)

- `UntrustedProposal` — typed, validated representation of a scrubbed model proposal (action, actor, capability token, nonce, sequence, timestamp, evidence, payload).
- `ProtocolState` — instance id, status, version, sequence, task id.
- `AcceptedTransition` — transition id, action, from/to status, effects, audit records.
- `RejectedProposal` — reason code (from the rejection taxonomy), failed checks, audit records.
- `AuditRecord` — append‑only decision record (decision, reason, actor, timestamp, hash chain field).

Full definitions in `src/protocol_gate/models.py`.

## 6. Interfaces

- **Kernel:** `ProtocolGate(spec, state_store, authority, evidence, effects).evaluate(proposal, *, scrub_actions=...)`.
- **Adapters (Protocols in `adapters/base.py`):** `StateStore`, `AuthorityAdapter`, `EvidenceAdapter`, `EffectAdapter`.
- **HTTP:** `POST /gate/evaluate`, `GET /state/{instance_id}`, `GET /health/{live,ready}`, `GET /metrics`.

## 7. Deployment & runtime

- Reference stack via `infra/docker-compose.yml`: Ollama, gate‑api, Prometheus, Grafana, Jaeger, Loki, Promtail, OTel Collector, MLflow.
- Multi‑stage `docker/Dockerfile` runs the API as a non‑root user with a healthcheck.
- Configuration via environment variables (see `.env.example`).

## 8. Testing strategy

- **Unit** — kernel steps, scrubber, state machine, audit.
- **Property (Hypothesis)** — fail‑closed, idempotency, audit completeness, authorization over randomized adversarial inputs.
- **Integration** — full lifecycle happy path + full rejection taxonomy.
- **Formal** — TLC model checking of safety + liveness.
- **Empirical** — A/B experiment harness + benchmarks.

## 9. Observability

- Metrics namespaced `protocol_gate_*` (see `benchmarks/metrics.py`).
- Traces via OTLP → OTel Collector → Jaeger.
- Structured logs → Promtail → Loki, surfaced in Grafana.
