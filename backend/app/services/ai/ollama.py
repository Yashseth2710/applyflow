"""Ollama provider — local, offline, and free of any quota."""

import logging

import httpx

from app.core.config import settings
from app.services.ai.base import AIBadOutput, AIProvider, AIUnavailable, Generation

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    """Runs against a model on this machine.

    Only usable where Ollama is installed, which rules out a small free host —
    a 3B model needs gigabytes of memory that a free tier does not have.
    """

    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL

    def generate(self, prompt: str, *, fast: bool = False, max_tokens: int = 2048) -> Generation:
        # One local model, so `fast` has nothing to switch to.
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": max_tokens},
                },
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            raise AIUnavailable(
                "The local model took too long. A larger model on this machine "
                "may be too slow to use here."
            ) from exc
        except httpx.HTTPError as exc:
            raise AIUnavailable("Could not reach Ollama. Is it running?") from exc

        if response.status_code == 404:
            raise AIUnavailable(f"Ollama has no model named {self.model}.")
        if response.status_code >= 400:
            logger.error("Ollama error %s: %s", response.status_code, response.text[:300])
            raise AIUnavailable("Ollama returned an error.")

        text = (response.json().get("response") or "").strip()
        if not text:
            raise AIBadOutput("The local model returned an empty answer.")

        return Generation(text=text, model=self.model)
