#!/usr/bin/env bash
#
# run_experiments.sh — run the control-vs-experiment A/B comparison and the
# benchmark suite, writing reports under ./results.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p results
export PYTHONPATH="src:."

echo "==> Running experiment comparison (control vs experiment)"
python -m experiments.runner | tee results/experiments.txt

echo "==> Running benchmark suite"
python -m benchmarks.runner --iterations "${ITERATIONS:-20}" --output results/benchmark.json

echo "==> Reports written to ./results/"
