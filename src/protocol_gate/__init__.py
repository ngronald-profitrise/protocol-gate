"""protocol_gate — the deterministic PAVSCE-A validation kernel.

The public surface is intentionally small: construct a :class:`ProtocolGate`
with a spec and adapters, then call :meth:`ProtocolGate.evaluate` with a scrubbed
proposal. Everything else is an implementation detail.
"""

from __future__ import annotations

from .audit import build_accepted_audit, build_rejected_audit, proposal_digest
from .kernel import STEPS, ProtocolGate
from .models import (
    AcceptedTransition,
    ActionType,
    AuditRecord,
    AuthenticatedContext,
    GateResult,
    HistoryEntry,
    ProtocolSpec,
    ProtocolState,
    ProtocolStatus,
    RejectedProposal,
    RejectionCode,
    TransitionRule,
    UntrustedProposal,
)
from .rejection import recovery_for
from .scrubber import ScrubResult, scrub
from .state_machine import StateMachine, TransitionComputation

__all__ = [
    "ProtocolGate",
    "STEPS",
    "ActionType",
    "ProtocolStatus",
    "RejectionCode",
    "ProtocolState",
    "ProtocolSpec",
    "TransitionRule",
    "UntrustedProposal",
    "AuthenticatedContext",
    "AcceptedTransition",
    "RejectedProposal",
    "GateResult",
    "HistoryEntry",
    "AuditRecord",
    "StateMachine",
    "TransitionComputation",
    "scrub",
    "ScrubResult",
    "recovery_for",
    "build_accepted_audit",
    "build_rejected_audit",
    "proposal_digest",
]

__version__ = "0.1.0"
