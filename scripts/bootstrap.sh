#!/usr/bin/env bash
#
# bootstrap.sh — set up a local development environment for Protocol Gate.
#
# Creates a virtualenv, installs the package with dev + bench extras, and runs
# a quick smoke check (import + unit tests). Idempotent: safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
VENV="${VENV:-.venv}"

echo "==> Creating virtualenv at ${VENV}"
"$PYTHON" -m venv "$VENV"
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

echo "==> Upgrading pip"
pip install --upgrade pip

echo "==> Installing project (dev + bench extras)"
pip install -e ".[dev,bench]"

echo "==> Running unit test smoke check"
PYTHONPATH="src:." python -m pytest tests/unit -q

cat <<'EOF'

Bootstrap complete.

Next steps:
  source .venv/bin/activate
  make test            # full test suite
  make up              # start the observability + inference stack
  scripts/pull_model.sh    # pull the default Ollama model
  scripts/run_experiments.sh
EOF
