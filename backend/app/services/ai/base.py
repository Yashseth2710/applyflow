"""The AI provider contract, and the errors callers have to handle."""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


class AIError(Exception):
    """Base for anything that stops a generation completing."""


class AIUnavailable(AIError):
    """The provider could not be reached, or is not configured."""


class AIRateLimited(AIError):
    """Quota exhausted. Expected on a free tier, not exceptional."""


class AIBadOutput(AIError):
    """The model answered, but not with anything we could use."""


@dataclass(frozen=True)
class Generation:
    text: str
    model: str


class AIProvider(ABC):
    """Text in, text out. Parsing and prompting live above this."""

    name: str

    @abstractmethod
    def generate(self, prompt: str, *, fast: bool = False, max_tokens: int = 2048) -> Generation:
        """Return the model's reply.

        `fast` asks for the cheaper model where the provider has one — fine for
        pulling facts out of text, less so for writing prose.
        """


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_json(text: str) -> dict | list:
    """Get JSON out of a model's reply.

    Models wrap JSON in prose, fence it as markdown, and trail commas. Treating
    the reply as well-formed JSON works right up until it doesn't, and then it
    is a 500 rather than a bad answer — so try progressively harder instead.
    """
    if not text or not text.strip():
        raise AIBadOutput("The model returned nothing.")

    candidates: list[str] = []

    fenced = _FENCE.search(text)
    if fenced:
        candidates.append(fenced.group(1))

    candidates.append(text)

    # Last resort: the outermost {...} or [...] in the reply.
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])

    for candidate in candidates:
        cleaned = candidate.strip()
        if not cleaned:
            continue

        for attempt in (
            cleaned,
            # Trailing commas before a closing brace or bracket are the single
            # most common malformation, and are trivially repairable.
            re.sub(r",(\s*[}\]])", r"\1", cleaned),
        ):
            try:
                parsed = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            # A bare number or string is valid JSON but not an answer, so keep
            # looking rather than handing back something unusable.
            if isinstance(parsed, dict | list):
                return parsed

    raise AIBadOutput("The model's reply was not valid JSON.")


def as_str_list(value: object, *, limit: int = 40) -> list[str]:
    """Coerce whatever came back into a list of non-empty strings.

    A field asked for as an array arrives as a string, or as objects with a
    "name" key, often enough that guarding here beats guarding at every use.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []

    out: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                for key in ("name", "skill", "title", "text", "value"):
                    if isinstance(item.get(key), str) and item[key].strip():
                        out.append(item[key].strip())
                        break
    return out[:limit]
