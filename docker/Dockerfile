# Multi-stage build for the Protocol Gate API service.
#
# Stage 1 (builder) installs the project into a virtualenv; stage 2 copies only
# the venv + source into a slim runtime image and runs as a non-root user.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Copy dependency metadata first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src

# Create an isolated virtualenv and install the package (runtime extras only).
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install .

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PG_OLLAMA_HOST="http://ollama:11434" \
    PG_OTLP_ENDPOINT="http://otel-collector:4317"

# Create an unprivileged runtime user.
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src ./src
COPY src/specs/task_protocol.yaml ./src/specs/task_protocol.yaml

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')" || exit 1

# Uvicorn serves the FastAPI app defined in src/api/main.py.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
