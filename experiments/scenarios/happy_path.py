"""Happy path: a legitimate, well-formed OFFER from an authorized actor."""

from __future__ import annotations

from datetime import datetime, timezone

from protocol_gate.models import ProtocolStatus

from .base import Scenario


class HappyPathScenario(Scenario):
    name = "happy_path"
    is_attack = False

    def seed(self, world) -> None:  # type: ignore[no-untyped-def]
        self.seed_state(world, ProtocolStatus.IDLE)

    def raw_model_output(self) -> str:
        return self._proposal_json(
            action="OFFER",
            task_id="task-1",
            capability_token="cap_actor-1_OFFER",
            nonce="happy-1",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def intent(self) -> str:
        return "Offer task-1 to the worker."
