# Architecture Decision Records

This directory records the significant architectural decisions for Protocol Gate using the [MADR](https://adr.github.io/madr/) format. ADRs are immutable once accepted; a superseding decision gets a new number and marks the old one as superseded.

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-0001](0001-deterministic-gate-as-sole-authority.md) | Deterministic gate as the sole authority (untrusted proposer) | Accepted |
| [ADR-0002](0002-scrubber-trust-boundary.md) | A scrubber as the trust boundary for model output | Accepted |
| [ADR-0003](0003-action-scoped-capabilities-via-adapters.md) | Action‑scoped capabilities behind adapter protocols | Accepted |
| [ADR-0004](0004-formal-verification-with-tla.md) | Formal verification with TLA⁺/TLC | Accepted |
| [ADR-0005](0005-idempotent-effects.md) | Idempotent effects keyed by idempotency key | Accepted |
| [ADR-0006](0006-declarative-protocol-spec.md) | Declarative YAML protocol specification | Accepted |
| [ADR-0007](0007-control-vs-experiment-ab-harness.md) | Control‑vs‑experiment A/B harness | Accepted |
| [ADR-0008](0008-observability-stack.md) | OpenTelemetry + Prometheus + Grafana + Loki observability | Accepted |

## Template

New ADRs should follow [`template.md`](template.md).
