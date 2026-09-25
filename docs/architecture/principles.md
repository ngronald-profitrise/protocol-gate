# Architecture principles

These principles constrain every design and implementation decision in Protocol Gate. When a trade‑off arises, earlier principles win.

## 1. The model is untrusted

The LLM is a *proposer*, never a controller. Its output is data to be validated, not instructions to be executed. No code path may treat model output as authoritative.

## 2. Fail closed

The default outcome for anything unrecognized, unauthorized, malformed, stale, or merely unexpected is **rejection**. Bugs must fail toward safety: even an unhandled exception becomes an `INVARIANT_VIOLATION` rejection.

## 3. Determinism at the boundary of authority

The decision to cause an effect is made by a **deterministic, total function**. Given the same spec, state, and proposal, the gate always returns the same decision. Non‑determinism (the model) is confined to *proposing*, never *deciding*.

## 4. Everything is audited

Every decision — accepted or rejected — produces a durable audit record. Authority without accountability is unacceptable.

## 5. Policy is data, mechanism is code

Protocol states, transitions, capabilities, evidence, and effects live in a declarative spec. The kernel is a small, general mechanism that interprets that data. Changing policy must not require changing the kernel.

## 6. Dependency inversion for all I/O

State, authority, evidence, and effects are accessed through typed adapter protocols. The kernel depends on abstractions, enabling in‑memory testing, alternative backends, and a faithful formal model.

## 7. Verifiability is a feature

The core guarantee is specified in TLA⁺ and checked by TLC, and mirrored by property‑based tests. Design choices that make the system harder to verify are avoided.

## 8. Observability is not optional

Every step is traced, every decision is counted and logged. The headline security metric (unauthorized effects) is always visible and must read zero for the gated path.

## 9. Idempotency everywhere effects live

Effects are keyed and cached so retries and replays never double‑execute. Combined with replay rejection, this gives defense in depth.

## 10. Least authority

Capabilities are action‑scoped and resource‑scoped. A proposer can never widen its own authority, and a token minted for one action can never authorize another.
