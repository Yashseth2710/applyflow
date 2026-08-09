"""AI providers.

One interface, three implementations, chosen by AI_PROVIDER:

    mock    tests and CI — deterministic, never touches a network
    ollama  local development — offline and private, needs Ollama running
    gemini  production — free tier, and the only one that fits a small host
"""

from app.core.config import settings
from app.services.ai.base import (
    AIBadOutput,
    AIError,
    AIProvider,
    AIRateLimited,
    AIUnavailable,
    Generation,
    as_str_list,
    parse_json,
)
from app.services.ai.gemini import GeminiProvider
from app.services.ai.mock import MockProvider
from app.services.ai.ollama import OllamaProvider
from app.services.ai.prompts import AITask

__all__ = [
    "AIBadOutput",
    "AIError",
    "AIProvider",
    "AIRateLimited",
    "AITask",
    "AIUnavailable",
    "Generation",
    "GeminiProvider",
    "MockProvider",
    "OllamaProvider",
    "as_str_list",
    "build_provider",
    "parse_json",
]


def build_provider(name: str | None = None) -> AIProvider:
    provider = name or settings.AI_PROVIDER
    if provider == "gemini":
        return GeminiProvider()
    if provider == "ollama":
        return OllamaProvider()
    return MockProvider()
