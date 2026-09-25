# Vision

## The world we want

A world where deploying an LLM agent that *acts* is as safe by default as deploying a web service behind an authorization layer. Today, "the model decides and we hope" is the norm. We want "the model proposes and a verified authority decides" to be the norm.

## What Protocol Gate is

Protocol Gate is a reference architecture and working harness that makes the untrusted‑proposer pattern concrete, testable, and provable. It is small enough to understand in an afternoon, formal enough to verify, and instrumented enough to operate in production.

## What success looks like

- Engineers reach for "gate the action" the way they reach for "authenticate the request."
- Security reviews of agent systems can point to an audit log and a model‑checked invariant, not a prompt.
- Prompt injection and authority escalation become *uninteresting* against gated systems because they cannot cross the boundary.

## Principles we will not trade away

- The model never gains authority.
- Fail closed.
- Every decision is auditable.
- The guarantee is verifiable, not merely asserted.

## Where this is heading

From a single‑node reference to a set of adapters and patterns that teams can drop into real agent stacks: cryptographic capabilities, tamper‑evident audit logs, richer protocol composition, and integrations with popular agent frameworks — always preserving the core guarantee. See the [roadmap](roadmap.md).
