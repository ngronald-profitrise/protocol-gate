"""Protocol spec loading and the bundled sample spec."""

from __future__ import annotations

from .loader import (
    SpecValidationError,
    load_default_spec,
    load_spec,
    load_spec_from_text,
)

__all__ = [
    "load_spec",
    "load_spec_from_text",
    "load_default_spec",
    "SpecValidationError",
]
