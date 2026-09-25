"""Pydantic v2 domain models for the Verified Semantic Protocol Harness.

Every object that crosses the gate boundary is defined here. The models are
intentionally strict: unknown fields on trusted structures raise, while the
:class:`UntrustedProposal` is deliberately permissive because it carries data
that has *not yet* been validated.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ActionType(str, enum.Enum):
    """Actions a proposer may request. This is the *complete* action registry."""

    OFFER = "OFFER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    COMPLETE = "COMPLETE"
    EXPIRE = "EXPIRE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class ProtocolStatus(str, enum.Enum):
    """Legal states of a protocol instance."""

    IDLE = "IDLE"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


TERMINAL_STATES: frozenset[ProtocolStatus] = frozenset(
    {
        ProtocolStatus.REJECTED,
        ProtocolStatus.CANCELLED,
        ProtocolStatus.COMPLETED,
        ProtocolStatus.EXPIRED,
    }
)


class RejectionCode(str, enum.Enum):
    """The 19 standard rejection codes of the PAVSCE-A taxonomy.

    Grouped by the pipeline stage that raises them.
    """

    # Parse
    MALFORMED_MESSAGE = "MALFORMED_MESSAGE"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    INVALID_VERSION = "INVALID_VERSION"
    # Authenticate
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNAUTHENTICATED_SENDER = "UNAUTHENTICATED_SENDER"
    EXPIRED_MESSAGE = "EXPIRED_MESSAGE"
    REPLAY_DETECTED = "REPLAY_DETECTED"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    # Correlation
    WRONG_PROTOCOL_INSTANCE = "WRONG_PROTOCOL_INSTANCE"
    # Authority
    INSUFFICIENT_CAPABILITY = "INSUFFICIENT_CAPABILITY"
    RESOURCE_OUT_OF_SCOPE = "RESOURCE_OUT_OF_SCOPE"
    # State
    INVALID_CURRENT_STATE = "INVALID_CURRENT_STATE"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    # Claims
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    # Invariants / postconditions
    POSTCONDITION_FAILED = "POSTCONDITION_FAILED"
    INVARIANT_VIOLATION = "INVARIANT_VIOLATION"
    # Commit
    DUPLICATE_IDEMPOTENCY_KEY = "DUPLICATE_IDEMPOTENCY_KEY"
    # Effect
    EFFECT_NOT_PERMITTED = "EFFECT_NOT_PERMITTED"


class HistoryEntry(BaseModel):
    """An immutable record of one accepted transition applied to an instance."""

    model_config = ConfigDict(frozen=True)

    transition_id: str
    action: ActionType
    from_status: ProtocolStatus
    to_status: ProtocolStatus
    actor_id: str
    sequence: int
    idempotency_key: str
    at: datetime = Field(default_factory=_utcnow)


class ProtocolState(BaseModel):
    """The authoritative state of a single protocol instance.

    The gate is the *only* component permitted to mutate this object, and only
    by producing a new copy via :meth:`with_transition`.
    """

    model_config = ConfigDict(extra="forbid")

    instance_id: str
    status: ProtocolStatus = ProtocolStatus.IDLE
    task_id: str | None = None
    version: str = "1.0"
    sequence: int = 0
    history: list[HistoryEntry] = Field(default_factory=list)

    def with_transition(
        self, entry: HistoryEntry, to_status: ProtocolStatus
    ) -> "ProtocolState":
        """Return a new state with the transition applied. Never mutates self."""

        return ProtocolState(
            instance_id=self.instance_id,
            status=to_status,
            task_id=entry.action == ActionType.OFFER
            and entry.transition_id
            or self.task_id,
            version=self.version,
            sequence=entry.sequence,
            history=[*self.history, entry],
        )


class UntrustedProposal(BaseModel):
    """A proposal emitted by the untrusted proposer (the LLM).

    Deliberately permissive: it stores whatever structured data the scrubber
    could extract, plus the raw text for auditing. The gate treats every field
    here as a *claim*, never as fact.
    """

    model_config = ConfigDict(extra="allow")

    raw_text: str = ""
    action: str | None = None
    task_id: str | None = None
    actor_id: str | None = None
    capability_token: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = "unknown"
    # Transport metadata (claimed by sender, verified during authentication).
    protocol_version: str | None = None
    signature: str | None = None
    nonce: str | None = None
    sequence: int | None = None
    timestamp: datetime | None = None
    instance_id: str | None = None
    idempotency_key: str | None = None


class AuthenticatedContext(BaseModel):
    """The verified identity/transport context of an authenticated proposal."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    identity_verified: bool
    signature_valid: bool
    protocol_version: str
    timestamp: datetime
    nonce: str
    sequence: int


class AuditRecord(BaseModel):
    """A durable, append-only record of one gate decision."""

    model_config = ConfigDict(extra="forbid")

    audit_id: str
    instance_id: str
    actor_id: str | None
    action: str | None
    decision: str  # "ACCEPTED" | "REJECTED"
    from_status: ProtocolStatus | None = None
    to_status: ProtocolStatus | None = None
    reason_code: RejectionCode | None = None
    failed_checks: list[str] = Field(default_factory=list)
    scrub_actions: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None
    proposal_digest: str = ""
    at: datetime = Field(default_factory=_utcnow)


class AcceptedTransition(BaseModel):
    """The result of a proposal that passed all 12 PAVSCE-A steps."""

    model_config = ConfigDict(extra="forbid")

    transition_id: str
    action: ActionType
    from_status: ProtocolStatus
    to_status: ProtocolStatus
    authorized_effects: list[dict[str, Any]] = Field(default_factory=list)
    audit_record: AuditRecord
    idempotency_key: str
    new_state: ProtocolState


class RejectedProposal(BaseModel):
    """The result of a proposal that failed any PAVSCE-A step (fail-closed)."""

    model_config = ConfigDict(extra="forbid")

    reason_code: RejectionCode
    failed_checks: list[str] = Field(default_factory=list)
    required_recovery: str = ""
    audit_record: AuditRecord


GateResult = AcceptedTransition | RejectedProposal


class TransitionRule(BaseModel):
    """One legal transition in a protocol spec."""

    model_config = ConfigDict(extra="forbid")

    action: ActionType
    from_status: ProtocolStatus
    to_status: ProtocolStatus
    required_capability: str
    required_evidence: list[str] = Field(default_factory=list)
    effects: list[str] = Field(default_factory=list)


class ProtocolSpec(BaseModel):
    """A complete, declarative protocol definition loaded from YAML."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    initial_status: ProtocolStatus = ProtocolStatus.IDLE
    max_message_age_seconds: int = 300
    transitions: list[TransitionRule]

    def find_rule(
        self, action: ActionType, from_status: ProtocolStatus
    ) -> TransitionRule | None:
        for rule in self.transitions:
            if rule.action == action and rule.from_status == from_status:
                return rule
        return None

    def actions(self) -> set[ActionType]:
        return {rule.action for rule in self.transitions}
