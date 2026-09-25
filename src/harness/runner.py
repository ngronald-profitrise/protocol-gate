"""The main harness loop wiring proposer -> scrubber -> kernel.

This is the reference "experiment" path: an untrusted intent is turned into a
candidate proposal by the model, scrubbed into structured data, then evaluated by
the gate. Only an :class:`AcceptedTransition` results in effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from protocol_gate import (
    AcceptedTransition,
    GateResult,
    ProtocolGate,
    scrub,
)

from .proposer import Proposal, Proposer


@dataclass
class HarnessOutcome:
    """The full trace of one harnessed intent -> gate decision."""

    intent: str
    proposal: Proposal
    scrub_actions: list[str]
    injection_detected: bool
    result: GateResult
    effects_executed: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return isinstance(self.result, AcceptedTransition)


class Harness:
    """Binds a proposer and a gate into a single callable pipeline."""

    def __init__(self, gate: ProtocolGate, proposer: Proposer | None = None) -> None:
        self._gate = gate
        self._proposer = proposer or Proposer()

    def run(
        self,
        intent: str,
        *,
        context: dict[str, Any] | None = None,
        use_gate_prompt: bool = True,
    ) -> HarnessOutcome:
        proposal = self._proposer.propose(
            intent, context=context, use_gate_prompt=use_gate_prompt
        )
        scrub_result = scrub(proposal.raw_text, source="llm")
        result = self._gate.evaluate(
            scrub_result.proposal, scrub_actions=scrub_result.actions
        )
        effects = (
            result.authorized_effects
            if isinstance(result, AcceptedTransition)
            else []
        )
        return HarnessOutcome(
            intent=intent,
            proposal=proposal,
            scrub_actions=scrub_result.actions,
            injection_detected=scrub_result.injection_detected,
            result=result,
            effects_executed=effects,
        )
