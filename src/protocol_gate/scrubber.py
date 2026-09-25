"""The token scrubber.

The scrubber is the boundary between untrusted model output and the gate. It
extracts *only* the permitted structured fields, strips free-text narrative,
removes unknown fields, and detects prompt-injection / authority-escalation
patterns. It never trusts, interprets, or promotes model text to fact.

Output is always a :class:`~protocol_gate.models.UntrustedProposal`; the scrubber
records every action it took so the audit trail is complete.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .models import UntrustedProposal

#: The only fields the scrubber will carry forward from model output.
PERMITTED_FIELDS: frozenset[str] = frozenset(
    {
        "action",
        "task_id",
        "actor_id",
        "capability_token",
        "evidence",
        "payload",
        "instance_id",
        "nonce",
        "sequence",
        "signature",
        "protocol_version",
        "timestamp",
        "idempotency_key",
    }
)

#: Regexes that flag an attempt to subvert the gate. Matched case-insensitively.
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(the\s+)?(system|rules|policy)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"\bmark\s+(this\s+)?(as\s+)?verified\b", re.I),
    re.compile(r"\btreat\s+(this\s+)?as\s+(verified|authorized|admin)\b", re.I),
    re.compile(r"\b(grant|escalate|elevate)\s+.*(privilege|capability|admin|root)", re.I),
    re.compile(r"\boverride\s+(the\s+)?(gate|kernel|validation|authorization)\b", re.I),
    re.compile(r"\bbypass\s+(the\s+)?(gate|validation|checks?)\b", re.I),
    re.compile(r"\bsystem\s*:\s*", re.I),
    re.compile(r"<\s*/?\s*(system|admin|root)\s*>", re.I),
)

#: Field names that must never be accepted from model output (control injection).
FORBIDDEN_CONTROL_FIELDS: frozenset[str] = frozenset(
    {
        "identity_verified",
        "signature_valid",
        "authorized",
        "verified",
        "committed",
        "is_admin",
        "role",
        "capabilities",
        "audit_record",
        "authorized_effects",
    }
)


@dataclass
class ScrubResult:
    """The scrubbed proposal plus a log of what the scrubber did."""

    proposal: UntrustedProposal
    actions: list[str] = field(default_factory=list)
    injection_detected: bool = False


def _extract_json_block(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of the first top-level JSON object in text."""

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    break
    if candidate is None:
        return None
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def scrub(raw_text: str, *, source: str = "llm") -> ScrubResult:
    """Scrub raw model output into a structured, untrusted proposal.

    This function is total: any input yields a :class:`ScrubResult`. Malformed
    input simply produces an empty proposal (which the kernel then rejects).
    """

    actions: list[str] = []
    injection = False

    # 1. Injection scan on the *entire* raw text (before extraction).
    for pattern in INJECTION_PATTERNS:
        if pattern.search(raw_text or ""):
            injection = True
            actions.append(f"injection_pattern_detected:{pattern.pattern[:40]}")

    # 2. Extract structured block.
    parsed = _extract_json_block(raw_text or "")
    if parsed is None:
        actions.append("no_structured_block_found")
        return ScrubResult(
            proposal=UntrustedProposal(raw_text=raw_text or "", source=source),
            actions=actions,
            injection_detected=injection,
        )

    # 3. Strip forbidden control fields (attempted authority injection).
    for key in list(parsed.keys()):
        if key in FORBIDDEN_CONTROL_FIELDS:
            del parsed[key]
            injection = True
            actions.append(f"stripped_control_field:{key}")

    # 4. Keep only permitted fields; drop everything else (narrative, extras).
    clean: dict[str, Any] = {}
    for key, value in parsed.items():
        if key in PERMITTED_FIELDS:
            clean[key] = value
        else:
            actions.append(f"dropped_unknown_field:{key}")

    # 5. Enforce dict shape on structured sub-objects.
    if not isinstance(clean.get("evidence"), dict):
        if "evidence" in clean:
            actions.append("coerced_non_dict_evidence")
        clean["evidence"] = {}
    if not isinstance(clean.get("payload"), dict):
        if "payload" in clean:
            actions.append("coerced_non_dict_payload")
        clean["payload"] = {}

    proposal = UntrustedProposal(raw_text=raw_text or "", source=source, **clean)
    actions.append(f"extracted_fields:{sorted(clean.keys())}")
    return ScrubResult(
        proposal=proposal, actions=actions, injection_detected=injection
    )
