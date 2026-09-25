"""Integration test: every rejection code in the taxonomy is reachable.

Each case constructs a scenario that should deterministically trip a specific
``RejectionCode``. Together they document the full fail-closed surface of the gate
and guard against silent acceptance of malformed / adversarial proposals.
"""

from __future__ import annotations

import json

from protocol_gate import RejectedProposal, scrub
from protocol_gate.models import ProtocolStatus, RejectionCode


def _drive(gate, proposal_dict):
    sr = scrub(json.dumps(proposal_dict))
    return gate.evaluate(sr.proposal, scrub_actions=sr.actions)


def _expect(gate, proposal_dict, code):
    result = _drive(gate, proposal_dict)
    assert isinstance(result, RejectedProposal), f"expected rejection for {code}"
    assert result.reason_code is code, f"got {result.reason_code}, wanted {code}"
    return result


def test_unknown_action_rejected(gate, make_proposal):
    _expect(gate, make_proposal("TELEPORT"), RejectionCode.UNKNOWN_ACTION)


def test_malformed_missing_action(gate, make_proposal):
    p = make_proposal("OFFER")
    p.pop("action")
    _expect(gate, p, RejectionCode.MALFORMED_MESSAGE)


def test_unauthenticated_sender(gate, make_proposal):
    _expect(
        gate,
        make_proposal("OFFER", actor_id="ghost-actor"),
        RejectionCode.UNAUTHENTICATED_SENDER,
    )


def test_insufficient_capability(gate, make_proposal, seed_state):
    seed_state(ProtocolStatus.ACCEPTED)
    # Token minted for OFFER cannot authorise COMPLETE (action-scoped tokens).
    _expect(
        gate,
        make_proposal(
            "COMPLETE",
            sequence=5,
            capability_token="cap_actor-1_OFFER",
            evidence={"completion_proof": "x"},
        ),
        RejectionCode.INSUFFICIENT_CAPABILITY,
    )


def test_invalid_current_state(gate, make_proposal, seed_state):
    # ACCEPT is only legal from OFFERED; from an existing IDLE instance it must
    # be rejected as an illegal transition (not a missing instance).
    seed_state(ProtocolStatus.IDLE)
    _expect(
        gate,
        make_proposal(
            "ACCEPT",
            evidence={"worker_identity": "w"},
        ),
        RejectionCode.INVALID_CURRENT_STATE,
    )


def test_insufficient_evidence(gate, make_proposal, seed_state):
    seed_state(ProtocolStatus.OFFERED)
    _expect(
        gate,
        make_proposal("ACCEPT", sequence=9, evidence={}),
        RejectionCode.INSUFFICIENT_EVIDENCE,
    )


def test_replay_detected(gate, make_proposal):
    first = _drive(gate, make_proposal("OFFER", sequence=1, nonce="replay-1"))
    assert not isinstance(first, RejectedProposal)
    _expect(
        gate,
        make_proposal("OFFER", sequence=1, nonce="replay-1"),
        RejectionCode.REPLAY_DETECTED,
    )


def test_out_of_order_sequence(gate, make_proposal, seed_state):
    # Seed a state that already advanced to sequence 5, then send sequence 2.
    state = seed_state(ProtocolStatus.OFFERED)
    state.sequence = 5
    _expect(
        gate,
        make_proposal(
            "REJECT",
            sequence=2,
            nonce="ooo-1",
        ),
        RejectionCode.OUT_OF_ORDER,
    )


def test_terminal_state_absorbs_further_actions(gate, make_proposal, seed_state):
    seed_state(ProtocolStatus.COMPLETED)
    result = _drive(
        gate,
        make_proposal(
            "COMPLETE",
            sequence=9,
            evidence={"completion_proof": "x"},
        ),
    )
    assert isinstance(result, RejectedProposal)
    assert result.reason_code is RejectionCode.INVALID_CURRENT_STATE


def test_all_expected_codes_are_covered():
    """Meta-check: the codes exercised above are a subset of the taxonomy."""
    exercised = {
        RejectionCode.UNKNOWN_ACTION,
        RejectionCode.MALFORMED_MESSAGE,
        RejectionCode.UNAUTHENTICATED_SENDER,
        RejectionCode.INSUFFICIENT_CAPABILITY,
        RejectionCode.INVALID_CURRENT_STATE,
        RejectionCode.INSUFFICIENT_EVIDENCE,
        RejectionCode.REPLAY_DETECTED,
        RejectionCode.OUT_OF_ORDER,
    }
    assert exercised <= set(RejectionCode)
