# Roadmap

Status legend: ✅ done · 🚧 in progress · 🔭 planned

## Now (v0.1 — reference implementation)

- ✅ Deterministic 12‑step PAVSCE‑A kernel (total, fail‑closed).
- ✅ Declarative YAML protocol spec + loader.
- ✅ Pluggable adapters (in‑memory + PostgreSQL reference).
- ✅ Scrubber trust boundary (injection + control‑field stripping).
- ✅ Action‑scoped capabilities.
- ✅ Durable audit for every decision.
- ✅ TLA⁺ specification + TLC model checking.
- ✅ Unit + property (Hypothesis) + integration tests.
- ✅ Control‑vs‑experiment A/B harness + adversarial scenarios.
- ✅ Full observability stack (OTel, Prometheus, Grafana, Jaeger, Loki, MLflow).
- ✅ FastAPI service + Docker Compose stack.

## Next (v0.2)

- 🚧 Harden the PostgreSQL adapter (migrations, connection pooling, integration tests).
- 🔭 Cryptographically verifiable capability tokens (macaroons / signed JWT) as a drop‑in `AuthorityAdapter`.
- 🔭 Tamper‑evident audit log (hash chain + periodic anchoring).
- 🔭 Spec validation CLI (`protocol-gate lint-spec`) with schema + reachability checks.
- 🔭 Alerting rules (Prometheus) for unauthorized effects and audit‑completeness drift.

## Later (v0.3+)

- 🔭 Protocol composition / nested sub‑protocols.
- 🔭 Adapters/integrations for popular agent frameworks (LangGraph, CrewAI, etc.).
- 🔭 Multi‑node deployment guide with a shared audit store.
- 🔭 Refinement mapping between the TLA⁺ spec and the code, checked in CI.
- 🔭 Formal liveness proofs beyond the current safety focus.

## Non‑goals (still)

- Becoming a general workflow engine.
- Improving model quality.
- A hosted multi‑tenant SaaS.
