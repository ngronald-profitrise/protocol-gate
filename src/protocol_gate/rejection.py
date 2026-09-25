"""The rejection taxonomy: recovery guidance for every standard code.

A :class:`~protocol_gate.models.RejectedProposal` carries a ``reason_code`` and a
human/agent readable ``required_recovery`` string. This module is the single
source of truth mapping codes to recovery guidance so the mapping cannot drift.
"""

from __future__ import annotations

from .models import RejectionCode

#: Maps every rejection code to actionable recovery guidance.
RECOVERY_GUIDANCE: dict[RejectionCode, str] = {
    RejectionCode.MALFORMED_MESSAGE: (
        "Resend a syntactically valid proposal with the required structured fields."
    ),
    RejectionCode.UNKNOWN_ACTION: (
        "Use one of the registered actions from the protocol spec."
    ),
    RejectionCode.UNKNOWN_FIELD: (
        "Remove fields not present in the registered field set and resend."
    ),
    RejectionCode.INVALID_VERSION: (
        "Match the protocol version advertised by the gate."
    ),
    RejectionCode.INVALID_SIGNATURE: (
        "Re-sign the message with a valid actor key."
    ),
    RejectionCode.UNAUTHENTICATED_SENDER: (
        "Authenticate the sender before submitting a proposal."
    ),
    RejectionCode.EXPIRED_MESSAGE: (
        "Refresh the timestamp/nonce; the message exceeded max_message_age."
    ),
    RejectionCode.REPLAY_DETECTED: (
        "The nonce was already consumed. Generate a fresh nonce."
    ),
    RejectionCode.OUT_OF_ORDER: (
        "Resubmit with a sequence number greater than the last accepted one."
    ),
    RejectionCode.WRONG_PROTOCOL_INSTANCE: (
        "Target the correct instance_id/task correlation."
    ),
    RejectionCode.INSUFFICIENT_CAPABILITY: (
        "Obtain a capability token that grants the requested action."
    ),
    RejectionCode.RESOURCE_OUT_OF_SCOPE: (
        "The capability does not cover this resource. Request a broader grant."
    ),
    RejectionCode.INVALID_CURRENT_STATE: (
        "This action is not legal from the instance's current state."
    ),
    RejectionCode.PRECONDITION_FAILED: (
        "A declared precondition was not satisfied. Inspect failed_checks."
    ),
    RejectionCode.INSUFFICIENT_EVIDENCE: (
        "Attach the required evidence artifacts for this transition."
    ),
    RejectionCode.POSTCONDITION_FAILED: (
        "The computed transition violated a postcondition; no effect applied."
    ),
    RejectionCode.INVARIANT_VIOLATION: (
        "The transition would violate a business invariant; rejected fail-closed."
    ),
    RejectionCode.DUPLICATE_IDEMPOTENCY_KEY: (
        "This idempotency key was already committed; the prior result stands."
    ),
    RejectionCode.EFFECT_NOT_PERMITTED: (
        "The requested effect is not in the deterministic effect set."
    ),
}


def recovery_for(code: RejectionCode) -> str:
    """Return recovery guidance for a code, never raising for unknown codes."""

    return RECOVERY_GUIDANCE.get(code, "Refer to the protocol specification.")
