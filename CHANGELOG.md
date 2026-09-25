# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-09-25

Initial scaffold of the Protocol Gate harness.

### Added
- Deterministic 12-step **PAVSCE-A** kernel (`src/protocol_gate/`): total, fail-closed decision function with a complete rejection taxonomy and durable audit for every decision.
- Trust-boundary **scrubber** that strips prompt-injection patterns and forbidden control fields from untrusted model output and records scrub actions.
- **Action-scoped capability** model preventing privilege escalation across actions.
- Pluggable **adapters** (`src/adapters/`): `StateStore`, `AuthorityAdapter`, `EvidenceAdapter`, `EffectAdapter` with in-memory and PostgreSQL reference implementations; effects are idempotent.
- Declarative **YAML protocol spec** (`src/specs/task_protocol.yaml`) + loader.
- **Harness** (`src/harness/`): Ollama client, proposer, and runner feeding proposals to the gate.
- **FastAPI** service (`src/api/`) exposing the gate with health and metrics endpoints and OpenTelemetry middleware.
- **Control-vs-experiment A/B framework** (`experiments/`) with adversarial scenarios: replay, prompt injection, authority escalation, state confusion, malformed proposal, plus a happy path.
- **Benchmark** suite (`benchmarks/`) with Prometheus metrics, runner, and reporter.
- **TLA+ specification** (`proofs/`) with a TLC config; SANY-parsed and TLC model-checked (no invariant violations).
- **Tests** (`tests/`): unit, property-based (Hypothesis), and integration — 42 tests.
- **Observability stack** (`infra/`): Docker Compose with Ollama, gate-api, Prometheus, Grafana, Jaeger, Loki, Promtail, OpenTelemetry Collector, and MLflow; three provisioned Grafana dashboards.
- **Dockerfiles** (`docker/`) for the service and the benchmark job.
- **Developer tooling**: `Makefile`, `scripts/` (bootstrap, run experiments, pull model, reset state), `pyproject.toml` with ruff/mypy/black/pytest config.
- **Document spine**: README, PRD, TRD (with traceability matrix), DESIGN, WIREFRAME, AGENTS/CLAUDE, architecture docs, and 8 ADRs.
- **Community health** files, CI/security/docs/benchmark GitHub Actions workflows (SHA-pinned), issue/PR templates, CODEOWNERS, and Dependabot.

[Unreleased]: https://github.com/ngronald-profitrise/protocol-gate/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ngronald-profitrise/protocol-gate/releases/tag/v0.1.0
