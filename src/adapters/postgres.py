"""Postgres-backed production adapters.

These mirror the in-memory adapters but persist to Postgres. They use psycopg
(v3) if it is installed; import is lazy so the package works without a database
in test/CI environments. Schema is created on first use via :func:`init_schema`.

The commit path uses a single transaction to make state + history + audit +
idempotency-key reservation atomic, satisfying the kernel's commit contract.
"""

from __future__ import annotations

import json
from typing import Any

from protocol_gate.models import (
    AuditRecord,
    AuthenticatedContext,
    HistoryEntry,
    ProtocolState,
    ProtocolStatus,
    UntrustedProposal,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS protocol_state (
    instance_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    task_id TEXT,
    version TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS protocol_history (
    transition_id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL REFERENCES protocol_state(instance_id),
    action TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    actor_id TEXT,
    action TEXT,
    decision TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    reason_code TEXT,
    failed_checks JSONB NOT NULL DEFAULT '[]',
    scrub_actions JSONB NOT NULL DEFAULT '[]',
    idempotency_key TEXT,
    proposal_digest TEXT NOT NULL,
    at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS consumed_nonces (
    actor_id TEXT NOT NULL,
    nonce TEXT NOT NULL,
    PRIMARY KEY (actor_id, nonce)
);
"""


def _connect(dsn: str) -> Any:
    try:
        import psycopg  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "psycopg is required for Postgres adapters. Install `psycopg[binary]`."
        ) from exc
    return psycopg.connect(dsn, autocommit=False)


def init_schema(dsn: str) -> None:
    conn = _connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


class PostgresStateStore:
    """A Postgres-backed :class:`~adapters.base.StateStore`."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn = _connect(dsn)

    def load(self, instance_id: str) -> ProtocolState | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT instance_id, status, task_id, version, sequence "
                "FROM protocol_state WHERE instance_id = %s",
                (instance_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                "SELECT transition_id, action, from_status, to_status, actor_id, "
                "sequence, idempotency_key, at FROM protocol_history "
                "WHERE instance_id = %s ORDER BY sequence ASC",
                (instance_id,),
            )
            history = [
                HistoryEntry(
                    transition_id=h[0],
                    action=h[1],
                    from_status=ProtocolStatus(h[2]),
                    to_status=ProtocolStatus(h[3]),
                    actor_id=h[4],
                    sequence=h[5],
                    idempotency_key=h[6],
                    at=h[7],
                )
                for h in cur.fetchall()
            ]
        return ProtocolState(
            instance_id=row[0],
            status=ProtocolStatus(row[1]),
            task_id=row[2],
            version=row[3],
            sequence=row[4],
            history=history,
        )

    def commit(
        self, state: ProtocolState, entry: HistoryEntry, audit: AuditRecord
    ) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO protocol_state (instance_id, status, task_id, version, sequence) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (instance_id) DO UPDATE SET status = EXCLUDED.status, "
                "task_id = EXCLUDED.task_id, sequence = EXCLUDED.sequence, updated_at = now()",
                (
                    state.instance_id,
                    state.status.value,
                    state.task_id,
                    state.version,
                    state.sequence,
                ),
            )
            cur.execute(
                "INSERT INTO protocol_history (transition_id, instance_id, action, "
                "from_status, to_status, actor_id, sequence, idempotency_key, at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    entry.transition_id,
                    state.instance_id,
                    entry.action.value,
                    entry.from_status.value,
                    entry.to_status.value,
                    entry.actor_id,
                    entry.sequence,
                    entry.idempotency_key,
                    entry.at,
                ),
            )
            self._insert_audit(cur, audit)
        self._conn.commit()

    def record_audit(self, audit: AuditRecord) -> None:
        with self._conn.cursor() as cur:
            self._insert_audit(cur, audit)
        self._conn.commit()

    @staticmethod
    def _insert_audit(cur: Any, audit: AuditRecord) -> None:
        cur.execute(
            "INSERT INTO audit_log (audit_id, instance_id, actor_id, action, decision, "
            "from_status, to_status, reason_code, failed_checks, scrub_actions, "
            "idempotency_key, proposal_digest, at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                audit.audit_id,
                audit.instance_id,
                audit.actor_id,
                audit.action,
                audit.decision,
                audit.from_status.value if audit.from_status else None,
                audit.to_status.value if audit.to_status else None,
                audit.reason_code.value if audit.reason_code else None,
                json.dumps(audit.failed_checks),
                json.dumps(audit.scrub_actions),
                audit.idempotency_key,
                audit.proposal_digest,
                audit.at,
            ),
        )

    def is_idempotency_key_used(self, key: str) -> bool:
        with self._conn.cursor() as cur:
            cur.execute("SELECT 1 FROM idempotency_keys WHERE key = %s", (key,))
            return cur.fetchone() is not None

    def reserve_idempotency_key(self, key: str) -> bool:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO idempotency_keys (key) VALUES (%s) ON CONFLICT DO NOTHING",
                (key,),
            )
            reserved = cur.rowcount == 1
        self._conn.commit()
        return reserved


class PostgresAuthorityAdapter:
    """Nonce replay protection persisted to Postgres; grants held in memory.

    Capability grants are configuration, not runtime state, so they are kept in
    memory here while nonces (which must survive restarts) live in Postgres.
    """

    def __init__(
        self,
        dsn: str,
        *,
        grants: dict[str, dict[str, set[str]]] | None = None,
        trusted_actors: set[str] | None = None,
        require_signature: bool = True,
    ) -> None:
        self._conn = _connect(dsn)
        self._grants = grants or {}
        self._trusted_actors = trusted_actors or set()
        self._require_signature = require_signature
        self._token_owner: dict[str, str] = {}

    def authenticate(
        self, proposal: UntrustedProposal, max_age_seconds: int
    ) -> AuthenticatedContext | None:
        from datetime import datetime, timezone

        if not proposal.actor_id or proposal.actor_id not in self._trusted_actors:
            return None
        if self._require_signature and not proposal.signature:
            return None
        if not proposal.nonce:
            return None
        ts = proposal.timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - ts).total_seconds() > max_age_seconds:
            return None
        return AuthenticatedContext(
            actor_id=proposal.actor_id,
            identity_verified=True,
            signature_valid=True,
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
        grants = self._grants.get(owner, {}).get(action, set())
        return "*" in grants or resource in grants

    def is_nonce_fresh(self, actor_id: str, nonce: str) -> bool:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM consumed_nonces WHERE actor_id = %s AND nonce = %s",
                (actor_id, nonce),
            )
            return cur.fetchone() is None

    def consume_nonce(self, actor_id: str, nonce: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO consumed_nonces (actor_id, nonce) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (actor_id, nonce),
            )
        self._conn.commit()
