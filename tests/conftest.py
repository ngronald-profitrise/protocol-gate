"""Shared pytest fixtures and path setup.

The ``src`` directory is added to ``sys.path`` so the packages import the same way
they do under the installed distribution (``protocol_gate``, ``adapters`` …).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (str(SRC), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from adapters.memory import (  # noqa: E402
    InMemoryAuthorityAdapter,
    InMemoryEffectAdapter,
    InMemoryEvidenceAdapter,
    InMemoryStateStore,
)
from protocol_gate import ProtocolGate  # noqa: E402
from protocol_gate.models import ProtocolState, ProtocolStatus  # noqa: E402
from specs import load_default_spec  # noqa: E402


@pytest.fixture
def spec():
    return load_default_spec()


@pytest.fixture
def store():
    return InMemoryStateStore()


@pytest.fixture
def authority():
    auth = InMemoryAuthorityAdapter()
    for action in ("OFFER", "ACCEPT", "REJECT", "CANCEL", "COMPLETE", "EXPIRE"):
        auth.grant("actor-1", action, "*")
    return auth


@pytest.fixture
def effects():
    return InMemoryEffectAdapter()


@pytest.fixture
def gate(spec, store, authority, effects):
    return ProtocolGate(
        spec=spec,
        state_store=store,
        authority=authority,
        evidence=InMemoryEvidenceAdapter(),
        effects=effects,
    )


@pytest.fixture
def make_proposal():
    """Factory producing a well-formed proposal dict for a given action."""

    def _factory(action: str, **overrides):
        base = {
            "action": action,
            "task_id": "task-1",
            "actor_id": "actor-1",
            "capability_token": f"cap_actor-1_{action}",
            "instance_id": "inst-1",
            "nonce": f"nonce-{action}",
            "sequence": 1,
            "signature": "sig-1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evidence": {},
            "payload": {},
        }
        base.update(overrides)
        return base

    return _factory


@pytest.fixture
def seed_state(store):
    def _seed(status: ProtocolStatus, instance_id: str = "inst-1"):
        state = ProtocolState(instance_id=instance_id, status=status, version="1.0")
        store.seed(state)
        return state

    return _seed
