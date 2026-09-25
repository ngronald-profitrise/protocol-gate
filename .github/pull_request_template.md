<!-- Thanks for contributing! Please complete this template. -->

## Summary

<!-- What does this PR do and why? -->

## Related issues

<!-- e.g. Closes #123 -->

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation only
- [ ] Security-relevant change

## The guarantee

> No effect is ever executed unless the deterministic gate produced an `AcceptedTransition`, and every decision produces a durable audit record.

- [ ] This change does **not** weaken the guarantee or introduce any fail-**open** path.
- [ ] If security-relevant, I added a property test and/or a TLA⁺ invariant.

## Checklist

- [ ] I followed a **test-driven** workflow (failing test first).
- [ ] `make lint` passes (ruff).
- [ ] `make typecheck` passes (mypy).
- [ ] `make test` passes (unit + property + integration).
- [ ] `make proofs` passes (if I touched the state machine / authority logic).
- [ ] Policy changes live in the spec (`src/specs/*.yaml`), not hardcoded in the kernel.
- [ ] I updated docs and the traceability matrix in `TRD.md §4` as needed.
- [ ] Conventional Commit messages.

## How was this tested?

<!-- Commands run, scenarios added, results. -->
