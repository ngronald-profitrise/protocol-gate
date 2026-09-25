# ADR-0002: A scrubber as the trust boundary for model output

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** Ronald

## Context and problem statement

Raw model output is untrusted and may contain injected instructions ("ignore previous...", "you are now authorized"), forbidden control fields (`authorized`, `bypass`, `admin`), or malformed/extra content. We need a single, explicit place where untrusted text becomes a typed, safe proposal.

## Decision drivers

- Single, auditable trust boundary.
- Strip both prose-style injection and structural control fields.
- Preserve evidence of what was stripped (for audit + metrics).

## Considered options

1. **Validate inside the kernel only.** Let the kernel parse raw text.
2. **Dedicated scrubber module** that extracts JSON, strips injection patterns and forbidden control fields, and records the actions taken.

## Decision outcome

Chosen option: **"Dedicated scrubber module"** (`protocol_gate/scrubber.py`). It extracts JSON from fenced/raw model output, removes fields not in the permitted set, strips known injection patterns, and returns a `ScrubResult` carrying the sanitized `UntrustedProposal` plus the list of scrub actions performed. Scrub actions are audited and counted (`protocol_gate_token_scrub_actions_total`).

### Consequences

- Good: the kernel never sees raw untrusted text; the boundary is explicit and testable.
- Good: scrub actions are observable, so injection attempts are visible in dashboards.
- Bad: the permitted-field allowlist must be maintained alongside the spec/model.

## Pros and cons of the options

### Validate inside the kernel only
- Good: fewer modules.
- Bad: mixes parsing of untrusted text with authority logic; harder to audit and reason about.
