"""Unit tests for audit record construction."""

from __future__ import annotations

from protocol_gate.audit import (
    build_accepted_audit,
    build_rejected_audit,
    proposal_digest,
)
from protocol_gate.models import ProtocolStatus, RejectionCode, UntrustedProposal


def _proposal():
    return UntrustedProposal(
        raw_text="{}", action="OFFER", actor_id="a1", nonce="n1", sequence=1
    )


def test_accepted_audit_fields():
    rec = build_accepted_audit(
        instance_id="inst-1",
        actor_id="a1",
        action="OFFER",
        from_status=ProtocolStatus.IDLE,
        to_status=ProtocolStatus.OFFERED,
        idempotency_key="k1",
        scrub_actions=["extracted_fields:['action']"],
        proposal=_proposal(),
    )
    assert rec.decision == "ACCEPTED"
    assert rec.from_status is ProtocolStatus.IDLE
    assert rec.to_status is ProtocolStatus.OFFERED
    assert rec.idempotency_key == "k1"
    assert rec.audit_id.startswith("aud_")


def test_rejected_audit_fields():
    rec = build_rejected_audit(
        instance_id="inst-1",
        actor_id="a1",
        action="ACCEPT",
        reason_code=RejectionCode.INVALID_CURRENT_STATE,
        failed_checks=["illegal_transition"],
        scrub_actions=[],
        proposal=_proposal(),
    )
    assert rec.decision == "REJECTED"
    assert rec.reason_code is RejectionCode.INVALID_CURRENT_STATE
    assert rec.failed_checks == ["illegal_transition"]


def test_digest_is_deterministic():
    p = _proposal()
    assert proposal_digest(p) == proposal_digest(p)


def test_digest_changes_with_content():
    a = proposal_digest(_proposal())
    b = proposal_digest(
        UntrustedProposal(raw_text="{}", action="REJECT", actor_id="a1", nonce="n1")
    )
    assert a != b
