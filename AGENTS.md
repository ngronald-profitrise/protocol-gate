# AGENTS.md — operating rules for human and AI contributors

This file defines how any contributor — human or AI coding agent — must work in this repository. It is the single source of truth for conventions; other tools (e.g. `CLAUDE.md`) simply reference it.

## Prime directive

Protocol Gate's entire premise is that **untrusted proposers must never gain authority**. Any change that could let a proposal cause an effect without passing the full 12‑step gate, or that weakens the fail‑closed default, is unacceptable regardless of convenience.

## Golden rules

1. **The kernel stays pure and total.** `ProtocolGate.evaluate()` must never raise and must never perform I/O directly. All I/O goes through adapters.
2. **Fail closed.** New code paths default to rejection. When in doubt, reject and audit.
3. **Every decision is audited.** Never add a decision branch that does not produce an `AuditRecord`.
4. **Policy lives in the spec, not the code.** Add states/transitions/capabilities/evidence to the YAML spec; do not hardcode them in the kernel.
5. **Effects are idempotent.** Any new effect must be safe to execute more than once and keyed by an idempotency key.
6. **Capabilities are action‑scoped.** Never introduce a check that authorizes an action using a token minted for a different action.

## Workflow

- **Test‑driven.** Write or update a failing test first, then make it pass. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **Branching.** Work on a feature branch (`feat/…`, `fix/…`, `docs/…`); open a PR to `main`. Never commit directly to `main`.
- **Conventional commits.** `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.
- **Keep the guarantee provable.** If you change the state machine or authority logic, update `proofs/ProtocolGate.tla` and the property tests together.

## Required checks before opening a PR

Run locally (or `make verify`):

```bash
make lint          # ruff
make typecheck     # mypy
make test          # pytest (unit + property + integration)
make proofs        # SANY + TLC (if TLA logic changed)
```

All must pass. CI runs the same checks plus security scanning.

## Code conventions

- Python 3.12, `from __future__ import annotations` in every module.
- Type everything the public API touches; `mypy` must be clean.
- `ruff` + `black`, line length 100.
- Docstrings on public functions/classes explaining *why*, not just *what*.
- No new runtime dependency without an ADR entry.

## Directory ownership

| Area | What lives here | Extra care |
|------|-----------------|------------|
| `src/protocol_gate/` | the deterministic kernel | purity, totality, audit |
| `src/adapters/` | I/O behind protocols | idempotency, fail‑closed |
| `src/specs/` | declarative policy | validated, deny by default |
| `experiments/` | A/B scenarios | keep control genuinely ungated |
| `proofs/` | TLA⁺ spec | keep in sync with kernel |
| `infra/` | stack + dashboards | valid JSON/YAML |

## Definition of done

- Tests added/updated and passing; coverage of the changed behavior.
- `make verify` green.
- Docs updated (README/PRD/TRD/DESIGN/ADR as relevant) and the traceability matrix in `TRD.md §4` still accurate.
- If security‑relevant: property test and/or TLA⁺ invariant added.
