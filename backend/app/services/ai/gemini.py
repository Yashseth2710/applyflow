"""Gemini provider, used in production."""

import logging

import httpx

from app.core.config import settings
from app.services.ai.base import (
    AIBadOutput,
    AIProvider,
    AIRateLimited,
    AIUnavailable,
    Generation,
)

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        fast_model: str | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.GEMINI_API_KEY).strip()
        self.model = model or settings.GEMINI_MODEL
        self.fast_model = fast_model or settings.GEMINI_FAST_MODEL

    def generate(self, prompt: str, *, fast: bool = False, max_tokens: int = 2048) -> Generation:
        if not self.api_key:
            raise AIUnavailable("No Gemini API key is configured.")

        model = self.fast_model if fast else self.model
        url = f"{settings.GEMINI_BASE_URL}/models/{model}:generateContent"

        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        # Low, not zero: these are extraction and drafting tasks
                        # where consistency matters more than invention.
                        "temperature": 0.3,
                        "maxOutputTokens": max_tokens,
                    },
                },
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            raise AIUnavailable("The AI service took too long to respond.") from exc
        except httpx.HTTPError as exc:
            raise AIUnavailable("Could not reach the AI service.") from exc

        if response.status_code == 429:
            raise AIRateLimited("The free AI quota is used up for now. Try again in a minute.")
        if response.status_code == 404:
            # Google retires models for new keys, so this is a configuration
            # problem rather than a transient one — say so plainly.
            raise AIUnavailable(
                f"The model {model} is not available on this key. "
                "Set GEMINI_MODEL to one your key can reach."
            )
        if response.status_code in (401, 403):
            raise AIUnavailable("The AI API key was rejected.")
        if response.status_code >= 400:
            logger.error("Gemini error %s: %s", response.status_code, response.text[:300])
            raise AIUnavailable("The AI service returned an error.")

        return Generation(text=_extract_text(response.json()), model=model)


def _extract_text(payload: dict) -> str:
    """Pull the reply out of Gemini's envelope.

    A 200 does not guarantee text: a response blocked by a safety filter, or one
    cut off at the token limit, comes back well-formed and empty.
    """
    candidates = payload.get("candidates") or []
    if not candidates:
        blocked = (payload.get("promptFeedback") or {}).get("blockReason")
        if blocked:
            raise AIBadOutput(f"The AI service declined this request ({blocked}).")
        raise AIBadOutput("The AI service returned no answer.")

    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()

    # Truncation is rejected even when there is text. A cut-off reply still
    # parses as JSON often enough — the salvage in parse_json will happily close
    # a half-finished object — and the result is a confident answer with fields
    # silently missing. An error the user can retry beats that.
    if candidate.get("finishReason") == "MAX_TOKENS":
        raise AIBadOutput("The answer was cut short before it finished. Try again.")

    if not text:
        raise AIBadOutput("The AI service returned an empty answer.")

    return text
