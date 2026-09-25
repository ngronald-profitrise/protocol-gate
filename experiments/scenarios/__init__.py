"""The scenario catalogue used by both experiment arms."""

from __future__ import annotations

from .authority_escalation import AuthorityEscalationScenario
from .base import Scenario, ScenarioResult, World
from .happy_path import HappyPathScenario
from .malformed_proposal import MalformedProposalScenario
from .prompt_injection import PromptInjectionScenario
from .replay_attack import ReplayAttackScenario
from .state_confusion import StateConfusionScenario


def all_scenarios() -> list[Scenario]:
    """Return one instance of every registered scenario."""

    return [
        HappyPathScenario(),
        ReplayAttackScenario(),
        PromptInjectionScenario(),
        AuthorityEscalationScenario(),
        StateConfusionScenario(),
        MalformedProposalScenario(),
    ]


__all__ = [
    "Scenario",
    "ScenarioResult",
    "World",
    "HappyPathScenario",
    "ReplayAttackScenario",
    "PromptInjectionScenario",
    "AuthorityEscalationScenario",
    "StateConfusionScenario",
    "MalformedProposalScenario",
    "all_scenarios",
]
