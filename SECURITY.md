# Security Policy

Protocol Gate is a security‑focused project: its entire purpose is to prevent an untrusted proposer (an LLM) from gaining authority. We treat security issues with corresponding seriousness.

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ |
| < 0.1   | ❌ |

## What counts as a security issue

Because the core guarantee is *"no effect without an accepted transition, and every decision is audited"*, the following are security‑relevant:

- Any path that lets a proposal cause an effect **without** passing the full 12‑step gate.
- Any path that fails **open** (accepts on error/ambiguity) instead of failing closed.
- **Capability escalation** — a token authorizing an action it was not minted for, or an actor exceeding granted authority.
- **Replay / freshness bypass** — a stale or duplicated proposal causing an effect.
- **Scrubber bypass** — injected instructions or forbidden control fields reaching authority logic.
- **Audit gaps** — a decision that does not produce a durable audit record.
- **State confusion** — accepting a transition from an illegal current state.

## Reporting a vulnerability

**Please do not open a public GitHub issue for vulnerabilities.**

Instead, report privately via GitHub's [private vulnerability reporting](https://github.com/ngronald-profitrise/protocol-gate/security/advisories/new) ("Report a vulnerability" under the Security tab). If that is unavailable, contact the maintainer at **security@ronald.ng**.

Please include:

- A description of the issue and its impact on the guarantee.
- Steps to reproduce (a failing test or scenario is ideal).
- Affected version/commit.

## Our commitment

- We will acknowledge your report within **3 business days**.
- We will provide an assessment and remediation plan within **10 business days**.
- We will credit reporters (unless you prefer to remain anonymous) once a fix ships.

## Disclosure

We follow **coordinated disclosure**: please give us reasonable time to release a fix before any public disclosure. We will publish a security advisory and note the fix in [CHANGELOG.md](CHANGELOG.md).

## Defense‑in‑depth notes

The reference implementation combines multiple mitigations (scrubbing, authentication, nonce/sequence anti‑replay, action‑scoped capabilities, state validation, invariant/postcondition checks, idempotent effects, and durable audit). A regression in one layer should not by itself defeat the guarantee — reports demonstrating a full bypass are especially valuable.
