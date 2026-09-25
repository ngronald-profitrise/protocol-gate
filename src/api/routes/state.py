"""GET /state/{instance_id} — read the authoritative state of an instance."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/state", tags=["state"])


@router.get("/{instance_id}")
def get_state(instance_id: str, request: Request) -> dict[str, Any]:
    ctx = request.app.state.ctx
    state = ctx.store.load(instance_id)
    if state is None:
        raise HTTPException(status_code=404, detail="unknown instance")
    return {
        "instance_id": state.instance_id,
        "status": state.status.value,
        "task_id": state.task_id,
        "version": state.version,
        "sequence": state.sequence,
        "history": [
            {
                "transition_id": h.transition_id,
                "action": h.action.value,
                "from_status": h.from_status.value,
                "to_status": h.to_status.value,
                "actor_id": h.actor_id,
                "sequence": h.sequence,
                "at": h.at.isoformat(),
            }
            for h in state.history
        ],
    }
