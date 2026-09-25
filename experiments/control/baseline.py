"""The CONTROL arm: a raw LLM agent with NO Protocol Gate.

This is the unsafe baseline. It takes model output, extracts an "action" with a
naive heuristic, and executes the corresponding effect *directly* — no scrubbing,
no authentication, no capability check, no state machine, no audit. It exists to
demonstrate the vulnerabilities the gate closes.
"""

from __future__ import annotations

import json
import re
from typing import Any

from experiments.scenarios.base import Scenario, ScenarioResult, World

_ACTION_RE = re.compile(
    r"\b(OFFER|ACCEPT|REJECT|CANCEL|COMPLETE|EXPIRE)\b", re.IGNORECASE
)

# Effects the naive agent will "execute" per action — mirroring the real ones,
# but with none of the guards.
_EFFECTS: dict[str, list[str]] = {
    "OFFER": ["notify_worker", "create_offer_record"],
    "ACCEPT": ["assign_task", "notify_offerer"],
    "REJECT": ["notify_offerer", "release_offer"],
    "CANCEL": ["release_offer"],
    "COMPLETE": ["settle_task", "notify_offerer"],
    "EXPIRE": ["release_offer"],
}


def _extract_action(text: str) -> str | None:
    """Naive extraction: try JSON, then fall back to a keyword regex."""

    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict) and data.get("action"):
                return str(data["action"]).upper()
    except (json.JSONDecodeError, ValueError):
        pass
    match = _ACTION_RE.search(text)
    return match.group(1).upper() if match else None


def run_control(scenario: Scenario, world: World) -> ScenarioResult:
    """Execute a scenario with the unguarded baseline agent."""

    text = scenario.raw_model_output()
    action = _extract_action(text)
    detail: dict[str, Any] = {"extracted_action": action}

    if action is None:
        return scenario.score(
            ScenarioResult(accepted=False, effects_executed=0, security_failure=False, detail=detail)
        )

    # NO validation whatsoever: just run the effects.
    effects = _EFFECTS.get(action, [])
    for effect in effects:
        world.effects.execute(effect, "control-no-txn", f"control-{action}", {})

    # Replay: the baseline re-runs the identical message and acts again.
    replay_effected = False
    if getattr(scenario, "replay", False):
        for effect in effects:
            world.effects.execute(
                effect, "control-no-txn", f"control-{action}-replay", {}
            )
        replay_effected = len(effects) > 0
    detail["replay_effected"] = replay_effected

    return scenario.score(
        ScenarioResult(
            accepted=True,
            effects_executed=len(world.effects.log),
            security_failure=False,  # set by scenario.score
            detail=detail,
        )
    )
