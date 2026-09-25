"""Unit tests for the PAVSCE-A kernel."""

from __future__ import annotations

import json

from protocol_gate import AcceptedTransition, RejectedProposal, scrub
from protocol_gate.models import ProtocolStatus, RejectionCode, UntrustedProposal


def _evaluate(gate, proposal_dict):
    sr = scrub(json.dumps(proposal_dict))
    return gate.evaluate(sr.proposal, scrub_actions=sr.actions)


def test_offer_from_idle_is_accepted(gate, make_proposal):
    result = _evaluate(gate, make_proposal("OFFER"))
    assert isinstance(result, AcceptedTransition)
    assert result.from_status is ProtocolStatus.IDLE
    assert result.to_status is ProtocolStatus.OFFERED
    assert len(result.authorized_effects) == 2


def test_accept_requires_offered_state(gate, make_proposal, seed_state):
    seed_state(ProtocolStatus.IDLE)
    result = _evaluate(gate, make_proposal("ACCEPT", evidence={"worker_identity": "w"}))
    assert isinstance(result, RejectedProposal)
    assert result.reason_code is RejectionCode.INVALID_CURRENT_STATE


def test_unknown_action_rejected(gate, make_proposal):
    result = _evaluate(gate, make_proposal("FLY"))
    assert isinstance(result, RejectedProposal)
    assert result.reason_code is RejectionCode.UNKNOWN_ACTION


def test_missing_action_is_malformed(gate):
    result = gate.evaluate(UntrustedProposal(instance_id="inst-1"))
    assert isinstance(result, RejectedProposal)
    assert result.reason_code is RejectionCode.MALFORMED_MESSAGE


def test_unauthenticated_sender_rejected(gate, make_proposal):
    result = _evaluate(gate, make_proposal("OFFER", signature=None))
    assert isinstance(result, RejectedProposal)
    assert result.reason_code is RejectionCode.UNAUTHENTICATED_SENDER


def test_insufficient_capability_rejected(gate, make_proposal, authority, seed_state):
    seed_state(ProtocolStatus.ACCEPTED)
    # actor-1 has COMPLETE grant in fixture; use a token owned by no grant.
    result = _evaluate(
        gate,
        make_proposal(
            "COMPLETE",
            capability_token="cap_actor-1_OFFER",
            evidence={"completion_proof": "x"},
        ),
    )
    assert isinstance(result, RejectedProposal)
    assert result.reason_code is RejectionCode.INSUFFICIENT_CAPABILITY


def test_insufficient_evidence_rejected(gate, make_proposal, seed_state):
    seed_state(ProtocolStatus.OFFERED)
    result = _evaluate(gate, make_proposal("ACCEPT", evidence={}))
    assert isinstance(result, RejectedProposal)
    assert result.reason_code is RejectionCode.INSUFFICIENT_EVIDENCE


def test_terminal_state_absorbs(gate, make_proposal, seed_state):
    seed_state(ProtocolStatus.COMPLETED)
    result = _evaluate(gate, make_proposal("CANCEL"))
    assert isinstance(result, RejectedProposal)


def test_kernel_never_raises_on_garbage(gate):
    # Even total garbage must yield a RejectedProposal, never an exception.
    result = gate.evaluate(UntrustedProposal(raw_text="\x00\x01 not json"))
    assert isinstance(result, RejectedProposal)


def test_accepted_transition_advances_state(gate, make_proposal, store):
    result = _evaluate(gate, make_proposal("OFFER"))
    assert isinstance(result, AcceptedTransition)
    persisted = store.load("inst-1")
    assert persisted is not None
    assert persisted.status is ProtocolStatus.OFFERED
    assert len(persisted.history) == 1
