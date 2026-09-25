"""GET /health and GET /metrics."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["ops"])


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    ctx = request.app.state.ctx
    return {
        "status": "ok",
        "spec": ctx.spec.name,
        "spec_version": ctx.spec.version,
        "actions": sorted(a.value for a in ctx.spec.actions()),
    }


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
