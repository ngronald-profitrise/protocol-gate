# ADR-0005: Idempotent effects keyed by idempotency key

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** Ronald

## Context and problem statement

Even with replay rejection at the gate, effect dispatch can be retried (crashes, at-least-once delivery). Effects that mutate the world must not double-execute.

## Decision drivers

- Exactly-once *observable* effect behavior under retries/replays.
- Defense in depth alongside nonce-based replay rejection.

## Considered options

1. **Best-effort, non-idempotent effects.**
2. **Idempotent effects** keyed by `(effect, idempotency_key)` with cached receipts.

## Decision outcome

Chosen option: **"Idempotent effects"**. The `EffectAdapter.execute(effect, transition_id, idempotency_key, payload)` contract requires idempotency; the reference `InMemoryEffectAdapter` caches receipts by `(effect, idempotency_key)` and returns the cached receipt on repeat. The idempotency key is derived from action + instance + nonce, so a replayed transition maps to the same key. Covered by `tests/property/test_idempotency.py` and `tests/integration/test_happy_path.py`.

### Consequences

- Good: retries and replays are safe; effects fire once.
- Bad: adapter authors must honor the idempotency contract for real side-effecting backends.

## Pros and cons of the options

### Best-effort, non-idempotent effects
- Bad: double execution under retries; unacceptable for effectful actions.
