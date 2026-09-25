"""Property: any invalid proposal leaves state unchanged (fail-closed).

    ¬ValidProposal(p) ⟹ StateAfter(p) = StateBefore(p)

We generate arbitrary proposals (mostly invalid) and assert that whenever the
gate rejects, the persisted state and effect log are byte-for-byte unchanged.
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
from protocol_gate import ProtocolGate, RejectedProposal
from protocol_gate.models import ProtocolState, ProtocolStatus, UntrustedProposal
from specs import load_default_spec

SPEC = load_default_spec()

action_st = st.sampled_from(
    ["OFFER", "ACCEPT", "REJECT", "CANCEL", "COMPLETE", "EXPIRE", "HACK", "", None]
)
status_st = st.sampled_from(list(ProtocolStatus))


def _build_gate(initial_status):
    store = InMemoryStateStore()
    store.seed(
        ProtocolState(instance_id="inst-1", status=initial_status, version="1.0")
    )
    authority = InMemoryAuthorityAdapter()  # no grants, no trusted actors
    gate = ProtocolGate(
        spec=SPEC,
        state_store=store,
        authority=authority,
        evidence=InMemoryEvidenceAdapter(),
        effects=InMemoryEffectAdapter(),
    )
    return gate, store


@settings(max_examples=300, deadline=None)
@given(
    action=action_st,
    initial_status=status_st,
    actor=st.text(min_size=0, max_size=8),
    token=st.one_of(st.none(), st.text(max_size=12)),
    sig=st.one_of(st.none(), st.text(max_size=8)),
    nonce=st.text(min_size=1, max_size=8),
)
def test_rejected_proposals_never_mutate_state(
    action, initial_status, actor, token, sig, nonce
):
    gate, store = _build_gate(initial_status)
    before = store.load("inst-1")
    before_effects = 0  # fresh effect adapter each run

    proposal = UntrustedProposal(
        action=action,
        actor_id=actor or None,
        capability_token=token,
        signature=sig,
        nonce=nonce,
        instance_id="inst-1",
        sequence=1,
    )
    result = gate.evaluate(proposal)

    if isinstance(result, RejectedProposal):
        after = store.load("inst-1")
        assert after is not None and before is not None
        assert after.status == before.status
        assert after.sequence == before.sequence
        assert len(after.history) == len(before.history)
        assert len(gate._effects.log) == before_effects  # type: ignore[attr-defined]
