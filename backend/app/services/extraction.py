"""Pulling plain text out of an uploaded resume.

The text is what the AI features read later, so it is extracted once at upload
time and stored, rather than reparsed on every request.
"""

import logging
import re
from dataclasses import dataclass
from typing import IO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.models.enums import ExtractionStatus

logger = logging.getLogger(__name__)

#: Below this, whatever came out is page furniture rather than a resume. Scanned
#: PDFs typically yield a handful of stray characters.
_MIN_USEFUL_CHARS = 100

#: Guards against a pathological file filling a database column.
_MAX_CHARS = 200_000

_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class ExtractionResult:
    status: ExtractionStatus
    text: str | None = None
    error: str | None = None
    pages: int | None = None


def _clean(raw: str) -> str:
    """PDF text arrives with the original layout's spacing baked in."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = _WHITESPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANK_LINES.sub("\n\n", text).strip()


def extract_pdf_text(source: IO[bytes]) -> ExtractionResult:
    """Never raises. A resume that cannot be read is still a resume worth
    keeping — the file is stored either way, and the user is told what happened.
    """
    try:
        reader = PdfReader(source)

        if reader.is_encrypted:
            # Some password-protected PDFs open with an empty password.
            try:
                if reader.decrypt("") == 0:
                    return ExtractionResult(
                        status=ExtractionStatus.FAILED,
                        error="This PDF is password protected, so its text could not be read.",
                    )
            except (PdfReadError, NotImplementedError):
                return ExtractionResult(
                    status=ExtractionStatus.FAILED,
                    error="This PDF uses an encryption method we cannot read.",
                )

        pages = len(reader.pages)
        parts: list[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 - one bad page shouldn't lose the rest
                logger.warning("Skipped an unreadable page while extracting resume text")

        text = _clean("\n".join(parts))

        if len(text) < _MIN_USEFUL_CHARS:
            return ExtractionResult(
                status=ExtractionStatus.EMPTY,
                pages=pages,
                error=(
                    "No readable text found. If this is a scanned or image-based "
                    "resume, export it as a text PDF and upload again."
                ),
            )

        return ExtractionResult(
            status=ExtractionStatus.OK,
            text=text[:_MAX_CHARS],
            pages=pages,
        )

    except PdfReadError as exc:
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            error=f"This file could not be read as a PDF: {exc}",
        )
    except Exception:
        logger.exception("Unexpected failure extracting resume text")
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            error="Something went wrong reading this file.",
        )
