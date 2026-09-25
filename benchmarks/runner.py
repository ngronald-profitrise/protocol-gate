"""Benchmark orchestrator.

Runs the A/B experiment N times (to gather latency distributions and stable
security metrics), writes a JSON artifact, prints a Markdown summary suitable for
a CI job summary, and optionally pushes metrics to a pushgateway.
"""

from __future__ import annotations

import argparse
import json

import yaml

from experiments.runner import run as run_experiment_suite

from . import reporter


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def run_benchmark(iterations: int) -> dict:
    """Run the suite ``iterations`` times and aggregate the last summary.

    Metrics accumulate across iterations in the shared registry (histograms build
    up their latency distributions); the returned summary is from the final pass.
    """

    summary = None
    for _ in range(max(1, iterations)):
        summary = run_experiment_suite()
    assert summary is not None
    return summary.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Protocol Gate benchmark suite")
    parser.add_argument("--config", default="benchmarks/scenarios.yaml")
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--output", default="benchmark_results.json")
    parser.add_argument("--summary-md", default=None, help="path for a Markdown summary")
    parser.add_argument("--push", action="store_true", help="push to pushgateway")
    args = parser.parse_args()

    iterations = args.iterations
    try:
        cfg = load_config(args.config)
        iterations = iterations or int(cfg.get("iterations", 20))
    except FileNotFoundError:
        iterations = iterations or 20

    summary = run_benchmark(iterations)
    reporter.to_json(summary, args.output)
    md = reporter.render_markdown(summary)
    print(md)
    if args.summary_md:
        with open(args.summary_md, "w", encoding="utf-8") as fh:
            fh.write(md)
    if args.push:
        pushed = reporter.push_to_gateway()
        print(f"pushgateway: {'pushed' if pushed else 'skipped'}")
    print("\nJSON summary:\n" + json.dumps(summary["summary"], indent=2))


if __name__ == "__main__":
    main()
