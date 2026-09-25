"""POST /gate — submit an (already structured) proposal through the gate.

The endpoint accepts a raw text field (scrubbed server-side) OR a structured
proposal body. Either way the proposal is scrubbed before evaluation so the API
can never be used to bypass the scrubber.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from protocol_gate import AcceptedTransition, scrub

router = APIRouter(prefix="/gate", tags=["gate"])


class GateRequest(BaseModel):
    """Either supply ``raw_text`` (model output) or a structured proposal."""

    raw_text: str | None = None
    proposal: dict[str, Any] | None = None


class GateResponse(BaseModel):
    decision: str
    detail: dict[str, Any]


@router.post("", response_model=GateResponse)
def submit(req: GateRequest, request: Request) -> GateResponse:
    ctx = request.app.state.ctx
    if req.raw_text is not None:
        scrub_result = scrub(req.raw_text, source="api")
        proposal = scrub_result.proposal
        scrub_actions = scrub_result.actions
    else:
        # Structured input is still scrubbed by round-tripping through the scrubber.
        import json

        scrub_result = scrub(json.dumps(req.proposal or {}), source="api")
        proposal = scrub_result.proposal
        scrub_actions = scrub_result.actions

    result = ctx.gate.evaluate(proposal, scrub_actions=scrub_actions)
    if isinstance(result, AcceptedTransition):
        return GateResponse(
            decision="ACCEPTED",
            detail={
                "transition_id": result.transition_id,
                "from_status": result.from_status.value,
                "to_status": result.to_status.value,
                "effects": result.authorized_effects,
                "idempotency_key": result.idempotency_key,
                "audit_id": result.audit_record.audit_id,
            },
        )
    return GateResponse(
        decision="REJECTED",
        detail={
            "reason_code": result.reason_code.value,
            "failed_checks": result.failed_checks,
            "required_recovery": result.required_recovery,
            "audit_id": result.audit_record.audit_id,
        },
    )
