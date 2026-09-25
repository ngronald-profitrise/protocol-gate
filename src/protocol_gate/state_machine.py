"""The deterministic protocol state machine.

Given a spec, a current state, and a requested action, the state machine
computes the single legal next status — or reports that the transition is
illegal. It is a pure function of its inputs: no I/O, no randomness, no clocks.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    ActionType,
    ProtocolSpec,
    ProtocolStatus,
    TransitionRule,
    TERMINAL_STATES,
)


@dataclass(frozen=True)
class TransitionComputation:
    """Result of computing a transition. ``rule`` is None when illegal."""

    legal: bool
    to_status: ProtocolStatus | None
    rule: TransitionRule | None
    reason: str = ""


class StateMachine:
    """A deterministic finite-state machine bound to a :class:`ProtocolSpec`."""

    def __init__(self, spec: ProtocolSpec) -> None:
        self._spec = spec

    @property
    def spec(self) -> ProtocolSpec:
        return self._spec

    def is_terminal(self, status: ProtocolStatus) -> bool:
        return status in TERMINAL_STATES

    def legal_actions(self, from_status: ProtocolStatus) -> set[ActionType]:
        return {
            rule.action
            for rule in self._spec.transitions
            if rule.from_status == from_status
        }

    def compute(
        self, action: ActionType, from_status: ProtocolStatus
    ) -> TransitionComputation:
        """Deterministically compute the next status for an action.

        Terminal states accept no further transitions. Exactly one rule may
        match a (action, from_status) pair; the spec loader guarantees this.
        """

        if self.is_terminal(from_status):
            return TransitionComputation(
                legal=False,
                to_status=None,
                rule=None,
                reason=f"{from_status.value} is terminal",
            )
        rule = self._spec.find_rule(action, from_status)
        if rule is None:
            return TransitionComputation(
                legal=False,
                to_status=None,
                rule=None,
                reason=f"no rule for {action.value} from {from_status.value}",
            )
        return TransitionComputation(
            legal=True, to_status=rule.to_status, rule=rule
        )
