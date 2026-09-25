# ADR-0006: Declarative YAML protocol specification

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** Ronald

## Context and problem statement

The set of states, transitions, required capabilities, required evidence, and effects is domain policy. If it lives in kernel code, every policy change is a code change, and the kernel stops being a general, verifiable mechanism.

## Decision drivers

- Policy changes should not require kernel changes.
- The spec should be human-readable and reviewable.
- The kernel should interpret data, not hardcode transitions.

## Considered options

1. **Hardcode transitions in the kernel.**
2. **Declarative YAML spec** loaded and validated at startup.
3. **Embedded DSL in Python.**

## Decision outcome

Chosen option: **"Declarative YAML spec"** (`src/specs/task_protocol.yaml` + `src/specs/loader.py`). The spec declares `initial_status`, `max_message_age_seconds`, and a list of transitions (action, from/to status, required capability, required evidence, effects). The state machine and kernel are driven entirely by the loaded spec.

### Consequences

- Good: policy is data; the kernel stays general and verifiable.
- Good: specs are easy to review and diff.
- Bad: the loader must validate structure and default to deny/fail-closed on malformed specs.

## Pros and cons of the options

### Hardcode transitions
- Bad: couples policy to code; harder to verify and to reuse.

### Embedded Python DSL
- Good: expressive.
- Bad: turns trusted config into code; larger attack/mistake surface.
