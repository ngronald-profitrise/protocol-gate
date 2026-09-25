"""YAML protocol-spec loader and validator.

Loads a :class:`~protocol_gate.models.ProtocolSpec` from YAML and validates two
structural invariants the kernel relies on:

1. No two transition rules share the same ``(action, from_status)`` pair — the
   state machine must be deterministic.
2. Every ``to_status`` and ``from_status`` is a legal :class:`ProtocolStatus`.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import yaml

from protocol_gate.models import ProtocolSpec


class SpecValidationError(ValueError):
    """Raised when a spec violates a structural invariant."""


def _validate(spec: ProtocolSpec) -> ProtocolSpec:
    seen: set[tuple[str, str]] = set()
    for rule in spec.transitions:
        key = (rule.action.value, rule.from_status.value)
        if key in seen:
            raise SpecValidationError(
                f"non-deterministic spec: duplicate rule for {key}"
            )
        seen.add(key)
    return spec


def load_spec_from_text(text: str) -> ProtocolSpec:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SpecValidationError("spec root must be a mapping")
    return _validate(ProtocolSpec.model_validate(data))


def load_spec(path: str | Path) -> ProtocolSpec:
    """Load a spec from a filesystem path."""

    return load_spec_from_text(Path(path).read_text(encoding="utf-8"))


def load_default_spec() -> ProtocolSpec:
    """Load the bundled ``task_protocol.yaml`` sample spec."""

    text = resources.files("specs").joinpath("task_protocol.yaml").read_text(
        encoding="utf-8"
    )
    return load_spec_from_text(text)
