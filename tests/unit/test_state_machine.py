"""Unit tests for the deterministic state machine."""

from __future__ import annotations

from protocol_gate.models import ActionType, ProtocolStatus
from protocol_gate.state_machine import StateMachine


def test_legal_offer(spec):
    sm = StateMachine(spec)
    comp = sm.compute(ActionType.OFFER, ProtocolStatus.IDLE)
    assert comp.legal
    assert comp.to_status is ProtocolStatus.OFFERED


def test_illegal_accept_from_idle(spec):
    sm = StateMachine(spec)
    comp = sm.compute(ActionType.ACCEPT, ProtocolStatus.IDLE)
    assert not comp.legal
    assert comp.to_status is None


def test_terminal_states_absorb(spec):
    sm = StateMachine(spec)
    for terminal in (
        ProtocolStatus.COMPLETED,
        ProtocolStatus.REJECTED,
        ProtocolStatus.CANCELLED,
        ProtocolStatus.EXPIRED,
    ):
        assert sm.is_terminal(terminal)
        comp = sm.compute(ActionType.CANCEL, terminal)
        assert not comp.legal


def test_legal_actions_from_offered(spec):
    sm = StateMachine(spec)
    actions = sm.legal_actions(ProtocolStatus.OFFERED)
    assert ActionType.ACCEPT in actions
    assert ActionType.REJECT in actions
    assert ActionType.OFFER not in actions


def test_full_happy_path_walk(spec):
    sm = StateMachine(spec)
    status = ProtocolStatus.IDLE
    for action in (ActionType.OFFER, ActionType.ACCEPT, ActionType.COMPLETE):
        comp = sm.compute(action, status)
        assert comp.legal, f"{action} illegal from {status}"
        status = comp.to_status
    assert status is ProtocolStatus.COMPLETED
