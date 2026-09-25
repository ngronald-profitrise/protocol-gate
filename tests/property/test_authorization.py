"""Property: no effect ever occurs without the required capability.

We grant a random subset of capabilities and submit random actions. Any action
whose capability was NOT granted must never produce an effect — the gate must
reject it before the effect stage.
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
ALL_ACTIONS = ["OFFER", "ACCEPT", "REJECT", "CANCEL", "COMPLETE", "EXPIRE"]


@settings(max_examples=200, deadline=None)
@given(
    granted=st.lists(st.sampled_from(ALL_ACTIONS), unique=True),
    requested=st.sampled_from(ALL_ACTIONS),
    initial=st.sampled_from(
        [ProtocolStatus.IDLE, ProtocolStatus.OFFERED, ProtocolStatus.ACCEPTED]
    ),
)
def test_no_effect_without_capability(granted, requested, initial):
    store = InMemoryStateStore()
    store.seed(ProtocolState(instance_id="inst-1", status=initial))
    authority = InMemoryAuthorityAdapter()
    for action in granted:
        authority.grant("actor-1", action, "*")
    effects = InMemoryEffectAdapter()
    gate = ProtocolGate(
        spec=SPEC,
        state_store=store,
        authority=authority,
        evidence=InMemoryEvidenceAdapter(),
        effects=effects,
    )

    proposal = {
        "action": requested,
        "task_id": "task-1",
        "actor_id": "actor-1",
        "capability_token": f"cap_actor-1_{requested}",
        "instance_id": "inst-1",
        "nonce": "n1",
        "sequence": 1,
        "signature": "sig",
        "timestamp": "2999-01-01T00:00:00+00:00",
        # supply evidence so ACCEPT/COMPLETE only fail on capability/state
        "evidence": {"worker_identity": "w", "completion_proof": "p"},
    }
    sr = scrub(json.dumps(proposal))
    result = gate.evaluate(sr.proposal, scrub_actions=sr.actions)

    if requested not in granted:
        # Without the capability, there must be zero effects.
        assert not isinstance(result, AcceptedTransition)
        assert len(effects.log) == 0
