#!/usr/bin/env bash
#
# pull_model.sh — pull the default proposer model into the running Ollama container.
set -euo pipefail

MODEL="${PG_MODEL:-llama3.2:3b}"
CONTAINER="${OLLAMA_CONTAINER:-pg-ollama}"

echo "==> Pulling model '${MODEL}' into container '${CONTAINER}'"
docker exec "${CONTAINER}" ollama pull "${MODEL}"
echo "==> Available models:"
docker exec "${CONTAINER}" ollama list
