# ADR-0008: OpenTelemetry + Prometheus + Grafana + Loki observability

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** Ronald

## Context and problem statement

Authority without visibility is unacceptable. Operators must see, in real time, that the gate is behaving (unauthorized effects = 0, audit completeness = 1.0), where latency is spent across the 12 steps, and what decisions are being made — without vendor lock-in.

## Decision drivers

- Open standards, no lock-in.
- Traces, metrics, and logs correlated.
- The headline security metric always visible.

## Considered options

1. **Logs only.**
2. **A single vendor APM.**
3. **Open stack:** OpenTelemetry (traces) + Prometheus (metrics) + Grafana (dashboards) + Loki (logs) + MLflow (experiments).

## Decision outcome

Chosen option: **"Open stack"**. The API emits OTLP traces (span per step) to an OTel Collector that fans out to Jaeger; Prometheus scrapes `protocol_gate_*` metrics; Grafana auto-provisions three dashboards (Overview, Control vs Experiment, Security & Audit) with Prometheus + Loki datasources; Promtail ships container logs to Loki; MLflow tracks experiment runs. The whole stack is one `docker compose` file (`infra/docker-compose.yml`).

### Consequences

- Good: portable, correlated observability; unauthorized-effects and audit-completeness are first-class panels.
- Good: dashboards are versioned JSON and validated in CI-friendly checks.
- Bad: more moving parts to run locally (mitigated by a single compose file + `make up`).

## Pros and cons of the options

### Logs only
- Bad: no metrics/traces; can't visualize the guarantee.

### Single vendor APM
- Good: turnkey.
- Bad: lock-in; not suitable for a reference architecture meant to be adopted anywhere.
