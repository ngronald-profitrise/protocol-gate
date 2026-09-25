# ADR-0004: Formal verification with TLA+/TLC

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** Ronald

## Context and problem statement

The core guarantee — no effect without an accepted transition, no illegal transition, fail-closed — should be more than asserted in tests. We want a machine-checked proof over the reachable state space, and we want it cheap enough to run in CI.

## Decision drivers

- Machine-checked safety invariants.
- Small enough to model-check on a laptop / in CI.
- Kept in sync with the implementation.

## Considered options

1. **Tests only.**
2. **TLA+ specification + TLC model checking** of the protocol state machine and authority rules.
3. **Interactive theorem proving (Coq/Isabelle).**

## Decision outcome

Chosen option: **"TLA+ + TLC"** (`proofs/ProtocolGate.tla`, `proofs/ProtocolGate.cfg`). The spec models actors, capabilities, states, and transitions, and TLC verifies safety invariants (no unauthorized effect, only legal transitions) plus basic liveness. The model targets the *same* invariants as the property tests to reduce drift. `make proofs` runs SANY (parse) + TLC (check); CI runs it too.

### Consequences

- Good: the guarantee is model-checked over all reachable states of the abstract model.
- Good: reviewers get a formal artifact, not just tests.
- Bad: the TLA+ model is an abstraction; a refinement mapping to the code is future work (roadmap). The AGENTS rules require updating the spec whenever the state machine/authority logic changes.

## Pros and cons of the options

### Tests only
- Bad: sample the input space; cannot prove absence of violations.

### Interactive theorem proving
- Good: strongest guarantee.
- Bad: far higher effort; overkill for the reference and not CI-friendly.
