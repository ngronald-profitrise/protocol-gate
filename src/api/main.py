"""FastAPI application factory for the Protocol Gate service.

Exposes the gate over HTTP with three route groups: ``/gate`` (submit a
proposal), ``/state`` (read instance state), and health/metrics. A single
shared :class:`AppContext` holds the spec, adapters, and gate so routes stay thin.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI

from adapters.memory import (
    InMemoryAuthorityAdapter,
    InMemoryEffectAdapter,
    InMemoryEvidenceAdapter,
    InMemoryStateStore,
)
from protocol_gate import ProtocolGate, ProtocolSpec
from specs import load_default_spec

from .middleware import RequestContextMiddleware


@dataclass
class AppContext:
    """The dependency container shared by all routes."""

    spec: ProtocolSpec
    store: InMemoryStateStore
    authority: InMemoryAuthorityAdapter
    evidence: InMemoryEvidenceAdapter
    effects: InMemoryEffectAdapter
    gate: ProtocolGate


def build_context(spec: ProtocolSpec | None = None) -> AppContext:
    spec = spec or load_default_spec()
    store = InMemoryStateStore()
    authority = InMemoryAuthorityAdapter()
    evidence = InMemoryEvidenceAdapter()
    effects = InMemoryEffectAdapter()
    gate = ProtocolGate(
        spec=spec,
        state_store=store,
        authority=authority,
        evidence=evidence,
        effects=effects,
    )
    return AppContext(
        spec=spec,
        store=store,
        authority=authority,
        evidence=evidence,
        effects=effects,
        gate=gate,
    )


def create_app(context: AppContext | None = None) -> FastAPI:
    ctx = context or build_context()
    app = FastAPI(
        title="Protocol Gate",
        version="0.1.0",
        description=(
            "Verified Semantic Protocol Harness — the LLM is an untrusted "
            "proposer; the gate is the only source of authority."
        ),
    )
    app.add_middleware(RequestContextMiddleware)
    app.state.ctx = ctx

    from .routes import gate, health, state

    app.include_router(health.router)
    app.include_router(gate.router)
    app.include_router(state.router)
    return app


# Module-level app for `uvicorn api.main:app`.
app = create_app()
