# Protocol Gate — documentation

Welcome to the Protocol Gate documentation. Protocol Gate is a **verified semantic protocol harness**: the LLM proposes, and a deterministic 12‑step gate decides.

## Start here

- [README](../README.md) — overview, quickstart, architecture.
- [PRD](../PRD.md) — product requirements.
- [TRD](../TRD.md) — technical requirements + traceability matrix.
- [DESIGN](../DESIGN.md) — system design.
- [WIREFRAME](../WIREFRAME.md) — operator & observability surfaces.
- [AGENTS](../AGENTS.md) — contributor/agent rules.

## Architecture

- [Principles](architecture/principles.md)
- [Vision](architecture/vision.md)
- [Roadmap](architecture/roadmap.md)
- [Building blocks](architecture/building-blocks.md)

## Decisions

- [Architecture Decision Records](adr/) — the "why" behind key choices.

## Formal verification

- [proofs/README](../proofs/README.md) — how to run SANY + TLC.

## Operations

- Run `make up` to start the full stack; see the README's quickstart for the list of URLs.
- Three Grafana dashboards are auto‑provisioned; see [WIREFRAME](../WIREFRAME.md).
