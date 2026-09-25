"""Benchmark result reporting: JSON artifact + optional Prometheus pushgateway.

The reporter serializes an :class:`ExperimentSummary` to JSON and, if a
pushgateway is configured, pushes the metric registry snapshot so a scheduled
benchmark job leaves durable series behind.
"""

from __future__ import annotations

import json
import os
from typing import Any

from . import metrics as M


def to_json(summary: dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)


def render_markdown(summary: dict[str, Any]) -> str:
    """Render a compact Markdown table for a PR comment / job summary."""

    lines = ["## Protocol Gate benchmark results", ""]
    lines.append("| Arm | Scenarios | Accepted | Security failures |")
    lines.append("|---|---|---|---|")
    for arm, stats in summary.get("summary", {}).items():
        lines.append(
            f"| `{arm}` | {stats['total_scenarios']} | {stats['accepted']} | "
            f"**{stats['security_failures']}** |"
        )
    lines.append("")
    lines.append("| Arm | Scenario | Accepted | Security failure |")
    lines.append("|---|---|---|---|")
    for rec in summary.get("records", []):
        flag = "❌" if rec["security_failure"] else "✅"
        lines.append(
            f"| `{rec['arm']}` | {rec['scenario']} | {rec['accepted']} | {flag} |"
        )
    return "\n".join(lines)


def push_to_gateway(job: str = "protocol_gate_benchmark") -> bool:
    """Push the metric registry to a Prometheus pushgateway if configured."""

    gateway = os.getenv("PUSHGATEWAY_URL")
    if not gateway:
        return False
    try:
        from prometheus_client import push_to_gateway as _push

        _push(gateway, job=job, registry=M.REGISTRY)
        return True
    except Exception:  # noqa: BLE001 - pushgateway optional
        return False
