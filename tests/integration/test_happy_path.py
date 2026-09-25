"""Integration test: a full task lifecycle driven through the gate.

Exercises the end-to-end pipeline (scrub -> evaluate -> commit -> effects)
across multiple transitions, asserting that state, effects, and the audit trail
all advance together.
"""

from __future__ import annotations

import json

from protocol_gate import AcceptedTransition, scrub
from protocol_gate.models import ProtocolStatus


def _drive(gate, proposal_dict):
    """Scrub a raw proposal string and evaluate it through the gate."""
    sr = scrub(json.dumps(proposal_dict))
    return gate.evaluate(sr.proposal, scrub_actions=sr.actions)


def test_full_offer_accept_complete_lifecycle(
    gate, make_proposal, store, effects
):
    # --- 1. OFFER: IDLE -> OFFERED -----------------------------------
    offer = _drive(
        gate,
        make_proposal("OFFER", sequence=1, nonce="n-offer"),
    )
    assert isinstance(offer, AcceptedTransition)
    assert offer.to_status is ProtocolStatus.OFFERED
    state = store.load("inst-1")
    assert state is not None
    assert state.status is ProtocolStatus.OFFERED

    # --- 2. ACCEPT: OFFERED -> ACCEPTED ------------------------------
    accept = _drive(
        gate,
        make_proposal(
            "ACCEPT",
            sequence=2,
            nonce="n-accept",
            evidence={"worker_identity": "worker-7"},
        ),
    )
    assert isinstance(accept, AcceptedTransition)
    assert accept.to_status is ProtocolStatus.ACCEPTED
    assert store.load("inst-1").status is ProtocolStatus.ACCEPTED

    # --- 3. COMPLETE: ACCEPTED -> COMPLETED --------------------------
    complete = _drive(
        gate,
        make_proposal(
            "COMPLETE",
            sequence=3,
            nonce="n-complete",
            evidence={"completion_proof": "artifact://done"},
        ),
    )
    assert isinstance(complete, AcceptedTransition)
    assert complete.to_status is ProtocolStatus.COMPLETED

    final = store.load("inst-1")
    assert final.status is ProtocolStatus.COMPLETED

    # Effects for every accepted transition must have been executed.
    executed = {entry["effect"] for entry in effects.log}
    assert {"notify_worker", "create_offer_record"} <= executed
    assert {"assign_task", "notify_offerer"} <= executed
    assert {"settle_task"} <= executed


def test_effects_are_idempotent_on_replayed_transition(gate, make_proposal, effects):
    """Re-submitting an already-committed transition must not double-fire effects."""
    first = _drive(gate, make_proposal("OFFER", sequence=1, nonce="dup-nonce"))
    assert isinstance(first, AcceptedTransition)
    count_after_first = len(effects.log)

    # Replay the exact same proposal (same nonce) -> must be rejected as replay,
    # so no new effects are recorded.
    replay = _drive(gate, make_proposal("OFFER", sequence=1, nonce="dup-nonce"))
    from protocol_gate import RejectedProposal

    assert isinstance(replay, RejectedProposal)
    assert len(effects.log) == count_after_first
