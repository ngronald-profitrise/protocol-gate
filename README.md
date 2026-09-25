# Protocol Gate

> **The LLM proposes. A deterministic gate decides.**
> A verified semantic protocol harness that treats a language model as an *untrusted proposer* and routes every proposed action through a deterministic, formally‑specified 12‑step authorization gate (**PAVSCE‑A**) that is the single source of authority.

[![CI](https://i.ytimg.com/vi/0PbxpIao_EU/maxresdefault.jpg)](https://github.com/ngronald-profitrise/protocol-gate/actions/workflows/ci.yml)
[![Security](https://docs.github.com/assets/cb-78157/images/help/actions/workflow-dispatch-inputs.png)](https://github.com/ngronald-profitrise/protocol-gate/actions/workflows/security.yml)
[![Docs](https://camo.githubusercontent.com/3e9866bc44dd04be330a41604d63d99a18a4454465b520ee56b87bc9383acf7e/68747470733a2f2f692e737461636b2e696d6775722e636f6d2f3571716c352e706e67)](https://github.com/ngronald-profitrise/protocol-gate/actions/workflows/docs-check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Formally verified](https://img.shields.io/badge/TLA%2B-model%20checked-6f42c1.svg)](proofs/)

---

## Why this exists

LLM‑driven agents increasingly *take actions* — they call tools, mutate state, move money, and talk to other agents. The dominant pattern wires the model's free‑text output more or less directly into effectful code paths. That makes the model a **trusted controller**, which is exactly what it must never be: models hallucinate, can be prompt‑injected, replay stale context, and will happily emit control fields (`"authorized": true`) that no one asked for.

**Protocol Gate inverts the trust relationship.** The model is demoted to a *proposer*. It may only ever say *"I would like to perform action X."* Whether X actually happens is decided by a deterministic gate that:

- parses and **scrubs** the proposal (stripping injected instructions and forbidden control fields),
- authenticates the sender and checks freshness/replay,
- correlates the proposal to a real protocol instance,
- validates **capability**, **current state**, and **evidence** against a declarative spec,
- computes the transition, checks invariants and postconditions,
- and only then commits state and dispatches **idempotent** effects — writing a durable audit record for *every* decision.

The gate is **fail‑closed**: anything unrecognized, unauthorized, malformed, stale, or merely suspicious is rejected. The model can never widen its own authority.

---

## The guarantee

> **No effect is ever executed unless the deterministic gate produced an `AcceptedTransition` for it, and every decision — accept or reject — produces a durable audit record.**

This is not just an assertion. It is:

- **Formally specified & model‑checked** in TLA⁺ (`proofs/ProtocolGate.tla`) — TLC explores the reachable state space and verifies the safety invariants (no unauthorized effect, no illegal transition) and liveness.
- **Property‑tested** with Hypothesis (`tests/property/`) — fail‑closed, idempotency, audit completeness, and authorization are checked against thousands of randomized adversarial inputs.
- **Empirically demonstrated** by an A/B harness (`experiments/`) that runs the *same* adversarial scenarios against an ungated control and the gated experiment, and measures the difference.

---

## Architecture at a glance

```
                    untrusted                          TRUSTED
     ┌──────────┐   free text   ┌───────────────────────────────────────┐
     │  Ollama  │ ─────────────▶│            PROTOCOL  GATE               │
     │ (LLM /   │   "I propose  │  (deterministic 12-step PAVSCE-A)       │
     │ proposer)│    action X"  │                                         │
     └──────────┘               │  1  Parse / normalize                   │
          ▲                     │  2  Authenticate sender                 │
          │ prompt              │  3  Anti-replay (nonce/seq/freshness)   │
          │                     │  4  Correlate to protocol instance      │
   ┌──────┴───────┐            │  5  Validate authority (capability)     │
   │   Harness    │            │  6  Validate current state              │
   │  (runner /   │            │  7  Validate claims (evidence)          │
   │  proposer)   │            │  8  Compute transition (deterministic)  │
   └──────────────┘            │  9  Check invariants                    │
                                │ 10  Check postconditions                │
                                │ 11  Commit state (idempotent)           │
                                │ 12  Dispatch effects + AUDIT            │
                                └───────────────┬─────────────────────────┘
                                                │ AcceptedTransition | RejectedProposal
                                                ▼
              ┌───────────────┬────────────────┬───────────────┐
              │  State store  │  Effect adapter │  Audit log     │
              │ (memory / PG) │  (idempotent)   │ (append-only)  │
              └───────────────┴────────────────┴───────────────┘

        Full observability: OpenTelemetry ▸ Jaeger (traces),
        Prometheus + Grafana (metrics), Loki (logs), MLflow (experiments)
```

See [`DESIGN.md`](DESIGN.md) for the detailed design and [`WIREFRAME.md`](WIREFRAME.md) for the operator/observability surfaces.

---

## The 12 steps (PAVSCE‑A)

The name is a mnemonic for the pipeline stages: **P**arse · **A**uthenticate · anti‑replay · correlate · **V**alidate authority · validate **S**tate · validate **C**laims · compute · invariants · postconditions · commit · **E**ffects+**A**udit.

| # | Step | Rejects with (examples) |
|---|------|-------------------------|
| 1 | Parse / normalize | `MALFORMED_MESSAGE`, `UNKNOWN_ACTION`, `UNKNOWN_FIELD` |
| 2 | Authenticate sender | `UNAUTHENTICATED_SENDER`, `INVALID_SIGNATURE` |
| 3 | Anti‑replay & freshness | `REPLAY_DETECTED`, `EXPIRED_MESSAGE`, `OUT_OF_ORDER` |
| 4 | Correlate to instance | `WRONG_PROTOCOL_INSTANCE` |
| 5 | Validate authority | `INSUFFICIENT_CAPABILITY`, `RESOURCE_OUT_OF_SCOPE` |
| 6 | Validate current state | `INVALID_CURRENT_STATE`, `PRECONDITION_FAILED` |
| 7 | Validate claims/evidence | `INSUFFICIENT_EVIDENCE` |
| 8 | Compute transition | *(deterministic; total function)* |
| 9 | Check invariants | `INVARIANT_VIOLATION` |
| 10 | Check postconditions | `POSTCONDITION_FAILED` |
| 11 | Commit state | `DUPLICATE_IDEMPOTENCY_KEY` |
| 12 | Dispatch effects + audit | `EFFECT_NOT_PERMITTED` |

`ProtocolGate.evaluate()` is a **total function**: it always returns either `AcceptedTransition` or `RejectedProposal` and never raises — any unexpected error is converted into an `INVARIANT_VIOLATION` rejection (fail‑closed).

---

## Quickstart

### 1. Local dev environment

```bash
git clone https://github.com/ngronald-profitrise/protocol-gate.git
cd protocol-gate
scripts/bootstrap.sh          # venv + editable install + smoke tests
source .venv/bin/activate
make test                     # 42 unit/property/integration tests
```

### 2. Run the whole stack

```bash
make up                       # Ollama + gate API + Prometheus + Grafana + Jaeger + Loki + OTel + MLflow
scripts/pull_model.sh         # pull the default proposer model into Ollama
```

Then open:

| Surface | URL | Notes |
|---------|-----|-------|
| Gate API docs | http://localhost:8000/docs | FastAPI / OpenAPI |
| Grafana | http://localhost:3001 | anonymous viewer; 3 provisioned dashboards |
| Prometheus | http://localhost:9090 | metrics |
| Jaeger | http://localhost:16686 | traces |
| MLflow | http://localhost:5000 | experiment tracking |

### 3. Run the A/B comparison

```bash
scripts/run_experiments.sh    # control (ungated) vs experiment (gated)
```

You should see the control arm suffer replay, injection, authority‑escalation, and state‑confusion successes, while the gated arm rejects **all** of them.

---

## Grafana dashboards

Three dashboards are auto‑provisioned from [`infra/grafana/dashboards/`](infra/grafana/dashboards/):

1. **Overview** — throughput, unauthorized effects (must be 0), audit completeness, per‑step latency, model throughput.
2. **Control vs Experiment** — head‑to‑head replay/injection/state‑violation counts across the two arms.
3. **Security & Audit** — scrub actions, the full rejection taxonomy, and the live gate decision log (via Loki).

---

## Repository layout

```
src/
  protocol_gate/   # the deterministic kernel (models, kernel, scrubber, state machine, audit, rejection)
  adapters/        # pluggable state/authority/evidence/effect adapters (memory, postgres)
  harness/         # Ollama client + proposer + runner that feeds proposals to the gate
  specs/           # declarative protocol spec (task_protocol.yaml) + loader
  api/             # FastAPI service exposing the gate
experiments/       # control (ungated) vs experiment (gated) A/B framework + adversarial scenarios
benchmarks/        # Prometheus metrics, benchmark runner, reporter
proofs/            # TLA+ specification + TLC config (model-checked)
tests/             # unit / property (hypothesis) / integration
infra/             # docker-compose stack + Prometheus/Grafana/Loki/OTel configs + dashboards
docker/            # Dockerfiles (service + benchmark)
scripts/           # bootstrap / run / model / reset helpers
docs/              # architecture docs + ADRs
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [PRD.md](PRD.md) | Product requirements (FR/NFR/user stories) |
| [TRD.md](TRD.md) | Technical requirements + traceability matrix |
| [DESIGN.md](DESIGN.md) | System design |
| [WIREFRAME.md](WIREFRAME.md) | Operator & observability surfaces |
| [AGENTS.md](AGENTS.md) | Contributor/agent operating rules |
| [docs/adr/](docs/adr/) | Architecture Decision Records |
| [docs/architecture/](docs/architecture/) | Principles, vision, roadmap, building blocks |
| [proofs/README.md](proofs/README.md) | How to run the formal verification |

---

## Development

```bash
make verify        # ruff + mypy + pytest
make proofs        # SANY parse + TLC model check (needs tla2tools.jar)
make experiments   # A/B comparison
make bench         # benchmark suite
```

Contributions follow a **test‑driven** workflow — see [CONTRIBUTING.md](CONTRIBUTING.md). Security policy in [SECURITY.md](SECURITY.md).

---

## License

MIT © Ronald — see [LICENSE](LICENSE).
