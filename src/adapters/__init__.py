"""Adapter interfaces and reference implementations for the Protocol Gate."""

from __future__ import annotations

from .base import (
    AuthorityAdapter,
    EffectAdapter,
    EvidenceAdapter,
    StateStore,
)
from .memory import (
    InMemoryAuthorityAdapter,
    InMemoryEffectAdapter,
    InMemoryEvidenceAdapter,
    InMemoryStateStore,
)

__all__ = [
    "StateStore",
    "AuthorityAdapter",
    "EvidenceAdapter",
    "EffectAdapter",
    "InMemoryStateStore",
    "InMemoryAuthorityAdapter",
    "InMemoryEvidenceAdapter",
    "InMemoryEffectAdapter",
]
