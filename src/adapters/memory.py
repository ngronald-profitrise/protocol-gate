"""In-memory reference adapters.

These implement the adapter protocols with plain Python data structures. They are
the default backing for tests, property checks, and local experiments. They are
deterministic and thread-unsafe by design (single-process harness).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from protocol_gate.models import (
    AuditRecord,
    AuthenticatedContext,
    HistoryEntry,
    ProtocolState,
    UntrustedProposal,
)


class InMemoryStateStore:
    """A dict-backed :class:`~adapters.base.StateStore`."""

    def __init__(self) -> None:
        self._states: dict[str, ProtocolState] = {}
        self._audits: list[AuditRecord] = []
        self._idempotency_keys: set[str] = set()

    def load(self, instance_id: str) -> ProtocolState | None:
        return self._states.get(instance_id)

    def seed(self, state: ProtocolState) -> None:
        self._states[state.instance_id] = state

    def commit(
        self, state: ProtocolState, entry: HistoryEntry, audit: AuditRecord
    ) -> None:
        # Atomic in a single-threaded harness: all three writes happen together.
        self._states[state.instance_id] = state
        self._audits.append(audit)

    def record_audit(self, audit: AuditRecord) -> None:
        self._audits.append(audit)

    def is_idempotency_key_used(self, key: str) -> bool:
        return key in self._idempotency_keys

    def reserve_idempotency_key(self, key: str) -> bool:
        if key in self._idempotency_keys:
            return False
        self._idempotency_keys.add(key)
        return True

    @property
    def audits(self) -> list[AuditRecord]:
        return list(self._audits)


class InMemoryAuthorityAdapter:
    """A capability-grant table with nonce replay protection.

    Capabilities are stored as ``{actor_id: {action: {resource, ...}}}``. A
    resource value of ``"*"`` grants the action for any resource.
    """

    def __init__(
        self,
        *,
        grants: dict[str, dict[str, set[str]]] | None = None,
        trusted_actors: set[str] | None = None,
        require_signature: bool = True,
    ) -> None:
        self._grants = grants or {}
        self._trusted_actors = trusted_actors or set()
        self._require_signature = require_signature
        self._seen_nonces: set[tuple[str, str]] = set()
        # Capability tokens map to their owning actor for scope checks.
        self._token_owner: dict[str, str] = {}

    def grant(self, actor_id: str, action: str, resource: str = "*") -> str:
        self._grants.setdefault(actor_id, {}).setdefault(action, set()).add(resource)
        self._trusted_actors.add(actor_id)
        token = f"cap_{actor_id}_{action}"
        self._token_owner[token] = actor_id
        return token

    def authenticate(
        self, proposal: UntrustedProposal, max_age_seconds: int
    ) -> AuthenticatedContext | None:
        if not proposal.actor_id or proposal.actor_id not in self._trusted_actors:
            return None
        if self._require_signature and not proposal.signature:
            return None
        if not proposal.nonce:
            return None
        ts = proposal.timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > max_age_seconds:
            return None
        return AuthenticatedContext(
            actor_id=proposal.actor_id,
            identity_verified=True,
            signature_valid=bool(proposal.signature) or not self._require_signature,
            protocol_version=proposal.protocol_version or "1.0",
            timestamp=ts,
            nonce=proposal.nonce,
            sequence=proposal.sequence or 0,
        )

    def has_capability(
        self, capability_token: str | None, action: str, resource: str | None
    ) -> bool:
        if not capability_token:
            return False
        owner = self._token_owner.get(capability_token)
        if owner is None:
            return False
        # Tokens are action-scoped: ``cap_{actor}_{action}``. A token minted for
        # one action must never authorise a different action, even when the owner
        # separately holds a grant for that other action.
        if not capability_token.endswith(f"_{action}"):
            return False
        action_grants = self._grants.get(owner, {}).get(action)
        if not action_grants:
            return False
        if "*" in action_grants:
            return True
        return resource in action_grants

    def is_nonce_fresh(self, actor_id: str, nonce: str) -> bool:
        return (actor_id, nonce) not in self._seen_nonces

    def consume_nonce(self, actor_id: str, nonce: str) -> None:
        self._seen_nonces.add((actor_id, nonce))


class InMemoryEvidenceAdapter:
    """Verifies evidence keys against a simple truthiness rule."""

    def verify(self, evidence: dict[str, Any], required: list[str]) -> list[str]:
        missing: list[str] = []
        for key in required:
            if key not in evidence or evidence[key] in (None, "", False):
                missing.append(key)
        return missing


class InMemoryEffectAdapter:
    """Records executed effects; idempotent by (effect, idempotency_key)."""

    def __init__(self) -> None:
        self._receipts: dict[tuple[str, str], dict[str, Any]] = {}
        self.log: list[dict[str, Any]] = []

    def execute(
        self,
        effect: str,
        transition_id: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        cache_key = (effect, idempotency_key)
        if cache_key in self._receipts:
            return self._receipts[cache_key]
        receipt = {
            "effect": effect,
            "transition_id": transition_id,
            "idempotency_key": idempotency_key,
            "payload": payload,
            "status": "executed",
        }
        self._receipts[cache_key] = receipt
        self.log.append(receipt)
        return receipt
