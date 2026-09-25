# ADR-0003: Action-scoped capabilities behind adapter protocols

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** Ronald

## Context and problem statement

Authority must be checked before state computation, and must not allow privilege widening. An early design checked only that the token's owner held *some* grant for the action, which allowed a token minted for one action to authorize another if the same actor happened to hold both grants. All authority/state access must also be swappable for different backends and for testing.

## Decision drivers

- Least authority; no privilege escalation.
- Testability and backend portability (dependency inversion).
- Cheap, early rejection.

## Considered options

1. **Owner-scoped tokens.** A token authorizes any action its owner is granted.
2. **Action-scoped tokens.** A token is bound to a specific action; `has_capability` requires both the owner's grant and that the token was minted for the requested action.
3. **Cryptographic capabilities (macaroons/JWT).**

## Decision outcome

Chosen option: **"Action-scoped tokens"**, implemented behind an `AuthorityAdapter` protocol (`adapters/base.py`, `adapters/memory.py`). Tokens are `cap_{actor}_{action}`; `has_capability(token, action, resource)` verifies the owner holds the grant **and** the token's action matches. Cryptographic capabilities are deferred to a future adapter (roadmap) — the interface already supports them.

### Consequences

- Good: closes the escalation hole (covered by `tests/property/test_authorization.py`).
- Good: adapters make the kernel pure and testable; postgres/crypto backends drop in.
- Bad: opaque tokens are not independently verifiable by third parties (acceptable for the reference).

## Pros and cons of the options

### Owner-scoped tokens
- Bad: allows cross-action escalation; rejected.

### Cryptographic capabilities
- Good: verifiable, revocable, portable.
- Bad: more complexity than needed to demonstrate the guarantee now; kept on the roadmap.
