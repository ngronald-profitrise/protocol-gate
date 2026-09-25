"""Abstract adapter interfaces.

The kernel is pure with respect to *policy* but must touch the outside world for
four things: reading/writing protocol state, checking authority, verifying
evidence, and executing effects. Each is behind a narrow interface so the kernel
can be exercised entirely in-memory during tests and property checks, and backed
by Postgres / real services in production.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from protocol_gate.models import (
    AuditRecord,
    AuthenticatedContext,
    HistoryEntry,
    ProtocolState,
    UntrustedProposal,
)


@runtime_checkable
class StateStore(Protocol):
    """Durable store for protocol instance state."""

    def load(self, instance_id: str) -> ProtocolState | None: ...

    def commit(
        self, state: ProtocolState, entry: HistoryEntry, audit: AuditRecord
    ) -> None:
        """Atomically persist the new state, its history entry, and audit record."""
        ...

    def is_idempotency_key_used(self, key: str) -> bool: ...

    def reserve_idempotency_key(self, key: str) -> bool:
        """Reserve a key. Returns False if already reserved (duplicate)."""
        ...


@runtime_checkable
class AuthorityAdapter(Protocol):
    """Capability-based authorization."""

    def authenticate(
        self, proposal: UntrustedProposal, max_age_seconds: int
    ) -> AuthenticatedContext | None:
        """Verify sender identity/signature/freshness. None => unauthenticated."""
        ...

    def has_capability(
        self, capability_token: str | None, action: str, resource: str | None
    ) -> bool: ...

    def is_nonce_fresh(self, actor_id: str, nonce: str) -> bool:
        """True if the nonce has not been seen (replay protection)."""
        ...

    def consume_nonce(self, actor_id: str, nonce: str) -> None: ...


@runtime_checkable
class EvidenceAdapter(Protocol):
    """Verifies that claimed evidence artifacts actually exist and are valid."""

    def verify(self, evidence: dict[str, Any], required: list[str]) -> list[str]:
        """Return the list of *missing or invalid* evidence keys (empty => ok)."""
        ...


@runtime_checkable
class EffectAdapter(Protocol):
    """Executes side effects — only ever the deterministic, authorized set."""

    def execute(
        self, effect: str, transition_id: str, idempotency_key: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute one effect and return a receipt. Must be idempotent by key."""
        ...
