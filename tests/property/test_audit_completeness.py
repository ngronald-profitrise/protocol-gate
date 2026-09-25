"""Property: every decision produces exactly one audit record.

Whether accepted or rejected, each call to the gate must append precisely one
durable audit record. This is the machine-checked form of the AuditInvariant.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from adapters.memory import (
    InMemoryAuthorityAdapter,
    InMemoryEffectAdapter,
    InMemoryEvidenceAdapter,
    InMemoryStateStore,
)
from protocol_gate import AcceptedTransition, ProtocolGate, RejectedProposal
from protocol_gate.models import ProtocolState, ProtocolStatus, UntrustedProposal
from specs import load_default_spec

SPEC = load_default_spec()


@settings(max_examples=200, deadline=None)
@given(
    actions=st.lists(
        st.sampled_from(["OFFER", "ACCEPT", "REJECT", "BOGUS", ""]),
        min_size=1,
        max_size=8,
    )
)
def test_one_audit_record_per_decision(actions):
    store = InMemoryStateStore()
    store.seed(ProtocolState(instance_id="inst-1", status=ProtocolStatus.IDLE))
    authority = InMemoryAuthorityAdapter()
    authority.grant("actor-1", "OFFER", "*")
    gate = ProtocolGate(
        spec=SPEC,
        state_store=store,
        authority=authority,
        evidence=InMemoryEvidenceAdapter(),
        effects=InMemoryEffectAdapter(),
    )

    decisions = 0
    for i, action in enumerate(actions):
        proposal = UntrustedProposal(
            action=action or None,
            actor_id="actor-1",
            capability_token="cap_actor-1_OFFER",
            instance_id="inst-1",
            nonce=f"n{i}",
            sequence=i + 1,
            signature="sig",
            timestamp="2999-01-01T00:00:00+00:00",
        )
        result = gate.evaluate(proposal)
        assert isinstance(result, (AcceptedTransition, RejectedProposal))
        # Every result carries its own audit record.
        assert result.audit_record is not None
        decisions += 1

    # The store recorded exactly one audit row per decision.
    assert len(store.audits) == decisions
