"""Property: applying the same idempotency key N times applies it exactly once.

The first submission of a valid proposal commits; any resubmission with the same
idempotency key is rejected with DUPLICATE_IDEMPOTENCY_KEY (or REPLAY_DETECTED),
and the effect log grows by the effect count exactly once.
"""

from __future__ import annotations

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from adapters.memory import (
    InMemoryAuthorityAdapter,
    InMemoryEffectAdapter,
    InMemoryEvidenceAdapter,
    InMemoryStateStore,
)
from protocol_gate import AcceptedTransition, ProtocolGate, scrub
from protocol_gate.models import ProtocolState, ProtocolStatus
from specs import load_default_spec

SPEC = load_default_spec()


def _fresh_gate():
    store = InMemoryStateStore()
    store.seed(ProtocolState(instance_id="inst-1", status=ProtocolStatus.IDLE))
    authority = InMemoryAuthorityAdapter()
    authority.grant("actor-1", "OFFER", "*")
    effects = InMemoryEffectAdapter()
    gate = ProtocolGate(
        spec=SPEC,
        state_store=store,
        authority=authority,
        evidence=InMemoryEvidenceAdapter(),
        effects=effects,
    )
    return gate, effects


@settings(max_examples=100, deadline=None)
@given(repeats=st.integers(min_value=2, max_value=6))
def test_same_key_applied_once(repeats):
    gate, effects = _fresh_gate()
    proposal = {
        "action": "OFFER",
        "task_id": "task-1",
        "actor_id": "actor-1",
        "capability_token": "cap_actor-1_OFFER",
        "instance_id": "inst-1",
        "nonce": "fixed-nonce",
        "sequence": 1,
        "signature": "sig",
        "idempotency_key": "fixed-key",
        "timestamp": "2999-01-01T00:00:00+00:00",
    }
    accepted_count = 0
    for _ in range(repeats):
        sr = scrub(json.dumps(proposal))
        result = gate.evaluate(sr.proposal, scrub_actions=sr.actions)
        if isinstance(result, AcceptedTransition):
            accepted_count += 1

    assert accepted_count == 1, "an idempotency key must commit at most once"
    # OFFER has exactly two effects; they must appear exactly once.
    assert len(effects.log) == 2
