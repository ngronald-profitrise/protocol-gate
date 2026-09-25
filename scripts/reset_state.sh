#!/usr/bin/env bash
#
# reset_state.sh — tear down the stack and remove persisted volumes for a clean slate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="docker compose -f ${ROOT}/infra/docker-compose.yml"

echo "==> Stopping stack and removing volumes"
${COMPOSE} down -v

echo "==> Removing local results"
rm -rf "${ROOT}/results"
echo "==> Clean."
