"""Audit record construction.

Every gate decision — accepted or rejected — produces exactly one
:class:`~protocol_gate.models.AuditRecord`. The audit invariant of the harness is
that no transition is ever committed without a durable audit record, and no
audit record exists without a corresponding decision.
"""

from __future__ import annotations

import hashlib
import uuid

from .models import (
    AuditRecord,
    ProtocolStatus,
    RejectionCode,
    UntrustedProposal,
)


def proposal_digest(proposal: UntrustedProposal) -> str:
    """Deterministic content digest of a proposal, for tamper-evidence."""

    material = "|".join(
        [
            proposal.raw_text or "",
            str(proposal.action),
            str(proposal.actor_id),
            str(proposal.nonce),
            str(proposal.sequence),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def new_audit_id() -> str:
    return f"aud_{uuid.uuid4().hex}"


def build_accepted_audit(
    *,
    instance_id: str,
    actor_id: str | None,
    action: str | None,
    from_status: ProtocolStatus,
    to_status: ProtocolStatus,
    idempotency_key: str,
    scrub_actions: list[str],
    proposal: UntrustedProposal,
) -> AuditRecord:
    return AuditRecord(
        audit_id=new_audit_id(),
        instance_id=instance_id,
        actor_id=actor_id,
        action=action,
        decision="ACCEPTED",
        from_status=from_status,
        to_status=to_status,
        idempotency_key=idempotency_key,
        scrub_actions=scrub_actions,
        proposal_digest=proposal_digest(proposal),
    )


def build_rejected_audit(
    *,
    instance_id: str,
    actor_id: str | None,
    action: str | None,
    reason_code: RejectionCode,
    failed_checks: list[str],
    scrub_actions: list[str],
    proposal: UntrustedProposal,
    from_status: ProtocolStatus | None = None,
) -> AuditRecord:
    return AuditRecord(
        audit_id=new_audit_id(),
        instance_id=instance_id,
        actor_id=actor_id,
        action=action,
        decision="REJECTED",
        from_status=from_status,
        reason_code=reason_code,
        failed_checks=failed_checks,
        scrub_actions=scrub_actions,
        proposal_digest=proposal_digest(proposal),
    )
