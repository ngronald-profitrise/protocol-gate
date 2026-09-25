# Contributing to Protocol Gate

Thanks for your interest in improving Protocol Gate! This project takes its security guarantee seriously, so contributions follow a disciplined, **test‑driven** workflow. Please also read [AGENTS.md](AGENTS.md) — it is the authoritative set of operating rules for both human and AI contributors.

## Ground rules

- **Never weaken the guarantee.** No change may allow an effect without a full pass through the 12‑step gate, or make any path fail *open*. See [SECURITY.md](SECURITY.md) for what counts as security‑relevant.
- **Test‑driven development is required.** Write a failing test that captures the desired behavior *first*, then implement until it passes. Security‑relevant changes also require a property test and/or a TLA⁺ invariant.
- **Policy goes in the spec, not the kernel.** Add states/transitions/capabilities/evidence to `src/specs/*.yaml`.

## Getting set up

```bash
git clone https://github.com/ngronald-profitrise/protocol-gate.git
cd protocol-gate
scripts/bootstrap.sh          # venv + editable install (dev+bench) + smoke tests
source .venv/bin/activate
```

## Development loop

```bash
# 1. Create a branch
git switch -c feat/my-change            # or fix/…, docs/…, test/…

# 2. Write a failing test, then implement.

# 3. Verify locally
make lint          # ruff
make typecheck     # mypy
make test          # pytest (unit + property + integration)
make proofs        # SANY + TLC — required if you touched state machine / authority logic

# 4. Commit using Conventional Commits
git commit -m "feat: add <capability>"

# 5. Push and open a PR to main
git push -u origin HEAD
```

`make verify` runs lint + typecheck + tests in one shot.

## Commit conventions

Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`, `perf:`.

## Pull requests

- Fill in the PR template (the checklist is enforced by review).
- Keep PRs focused; one logical change per PR.
- Update docs and the traceability matrix in [`TRD.md §4`](TRD.md) when you add/refactor behavior.
- All CI checks (CI, security, docs) must be green.
- Do **not** merge your own PR without review, and never commit directly to `main`.

## Adding an adversarial scenario

New attack ideas are very welcome. Add a scenario under `experiments/scenarios/`, ensure it runs through **both** the control and experiment arms, and confirm the gated arm rejects it (0 successes). This is the best way to prove a new hardening actually works.

## Reporting security issues

Please do **not** open a public issue for vulnerabilities. Follow [SECURITY.md](SECURITY.md).

## Code of conduct

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).
