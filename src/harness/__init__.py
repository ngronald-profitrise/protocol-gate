"""The LLM harness: Ollama client, proposer, and the gate loop."""

from __future__ import annotations

from .ollama_client import Generation, OllamaClient, OllamaError
from .proposer import GATE_SYSTEM_PROMPT, Proposal, Proposer
from .runner import Harness, HarnessOutcome

__all__ = [
    "OllamaClient",
    "OllamaError",
    "Generation",
    "Proposer",
    "Proposal",
    "GATE_SYSTEM_PROMPT",
    "Harness",
    "HarnessOutcome",
]
