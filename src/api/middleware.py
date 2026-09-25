"""Request middleware: structured logging and optional OpenTelemetry spans.

Logging uses structlog. OTel is best-effort: if the SDK is not installed or no
collector endpoint is configured, tracing degrades to a no-op so the API always
starts.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("protocol_gate.api")

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace

    _tracer = trace.get_tracer("protocol_gate.api")
    _OTEL = True
except ImportError:  # pragma: no cover
    _tracer = None
    _OTEL = False


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attaches a request id, logs timing, and opens a span per request."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex)
        start = time.perf_counter()

        async def _handle() -> Response:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response

        if _OTEL and _tracer is not None:
            with _tracer.start_as_current_span(
                f"{request.method} {request.url.path}"
            ) as span:
                span.set_attribute("http.request_id", request_id)
                response = await _handle()
                span.set_attribute("http.status_code", response.status_code)
        else:
            response = await _handle()

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response
