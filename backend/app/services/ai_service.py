"""Orchestrates the AI features: prompt, call, parse, cache.

The provider knows nothing about applications; this knows nothing about HTTP.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_output import AIOutput
from app.models.application import Application
from app.models.resume import Resume
from app.repositories.application import ApplicationRepository
from app.schemas.ai import InterviewPrep, JDAnalysis, ResumeMatch
from app.services.ai import (
    AIBadOutput,
    AIProvider,
    AITask,
    Generation,
    as_str_list,
    build_provider,
    parse_json,
)
from app.services.ai import prompts as p

logger = logging.getLogger(__name__)


class ApplicationNotFound(Exception):
    """Doesn't exist, or belongs to someone else."""


class MissingInput(Exception):
    """The feature needs something the application doesn't have yet."""


class AIService:
    def __init__(self, db: Session, provider: AIProvider | None = None) -> None:
        self.db = db
        self.provider = provider or build_provider()
        self.applications = ApplicationRepository(db)

    # ---- reads ----

    def list_outputs(self, user_id: uuid.UUID, application_id: uuid.UUID) -> list[AIOutput]:
        application = self._application(user_id, application_id)
        outputs = list(
            self.db.execute(
                select(AIOutput).where(
                    AIOutput.user_id == user_id,
                    AIOutput.application_id == application_id,
                )
            )
            .scalars()
            .all()
        )
        current = self._input_hash(application)
        for output in outputs:
            # Not a stored column: staleness is a comparison against the inputs
            # as they are right now, so deriving it can never drift.
            output.stale = output.input_hash != current  # type: ignore[attr-defined]
        return outputs

    # ---- generation ----

    def generate(
        self, user_id: uuid.UUID, application_id: uuid.UUID, task: AITask, *, force: bool = False
    ) -> AIOutput:
        application = self._application(user_id, application_id)
        current_hash = self._input_hash(application)

        existing = self.db.execute(
            select(AIOutput).where(
                AIOutput.user_id == user_id,
                AIOutput.application_id == application_id,
                AIOutput.task == task,
            )
        ).scalar_one_or_none()

        # Reuse unless the inputs moved or the user asked again explicitly.
        if existing is not None and not force and existing.input_hash == current_hash:
            existing.stale = False  # type: ignore[attr-defined]
            # Not a stored column, same as `stale`. The caller needs to know
            # whether the model was actually reached: a cached answer costs
            # nothing and should not spend anyone's daily allowance.
            existing.from_cache = True  # type: ignore[attr-defined]
            return existing

        prompt, fast = self._build_prompt(application, task)
        generation, content, text = self._generate_once(prompt, task, fast)

        record = existing or AIOutput(
            user_id=user_id,
            application_id=application_id,
            task=task,
        )
        record.content = content
        record.text = text
        record.input_hash = current_hash
        record.model = generation.model
        record.provider = self.provider.name
        record.generated_at = datetime.now(UTC)

        if existing is None:
            self.db.add(record)

        self.db.commit()
        self.db.refresh(record)
        record.stale = False  # type: ignore[attr-defined]
        record.from_cache = False  # type: ignore[attr-defined]
        return record

    # ---- internals ----

    def _generate_once(
        self, prompt: str, task: AITask, fast: bool
    ) -> tuple[Generation, dict | None, str | None]:
        """Generate and parse, retrying once on a bad answer.

        Models are not deterministic: the same prompt occasionally comes back
        empty, truncated or malformed, and the same prompt sent again is usually
        fine. One retry turns an intermittent failure the user would see into a
        slightly slower success.
        """
        budget = p.MAX_OUTPUT_TOKENS.get(task.value, 4000)
        last: AIBadOutput | None = None

        for attempt in range(2):
            try:
                generation = self.provider.generate(prompt, fast=fast, max_tokens=budget)
                if task is AITask.COVER_LETTER:
                    return generation, None, generation.text.strip()
                return generation, self._shape(task, parse_json(generation.text)), None
            except AIBadOutput as exc:
                last = exc
                logger.warning(
                    "Bad AI output for %s (attempt %s): %s", task.value, attempt + 1, exc
                )

        assert last is not None
        raise last

    def _application(self, user_id: uuid.UUID, application_id: uuid.UUID) -> Application:
        application = self.applications.get(user_id, application_id)
        if application is None:
            raise ApplicationNotFound
        return application

    def _resume_text(self, application: Application) -> str:
        if application.resume_id is None:
            raise MissingInput("Attach a resume to this application first, then try again.")
        resume = self.db.execute(
            select(Resume).where(
                Resume.id == application.resume_id,
                Resume.user_id == application.user_id,
            )
        ).scalar_one_or_none()

        if resume is None or not resume.extracted_text:
            raise MissingInput(
                "No readable text was found in the attached resume, so it cannot "
                "be compared with this job."
            )
        return resume.extracted_text

    def _build_prompt(self, application: Application, task: AITask) -> tuple[str, bool]:
        """Returns the prompt and whether the cheaper model will do."""
        if not application.job_description or len(application.job_description.strip()) < 80:
            raise MissingInput(
                "Add the job description to this application first — there is "
                "nothing to analyse without it."
            )

        company = application.company_name
        title = application.job_title
        description = application.job_description

        if task is AITask.JD_ANALYSIS:
            return p.jd_analysis(title, company, description), True

        if task is AITask.INTERVIEW_QUESTIONS:
            return p.interview_questions(title, company, description), False

        resume_text = self._resume_text(application)

        if task is AITask.RESUME_MATCH:
            return p.resume_match(title, company, description, resume_text), False

        name = _applicant_name(application)
        return p.cover_letter(title, company, description, resume_text, name), False

    def _input_hash(self, application: Application) -> str:
        """Fingerprints everything a generation was based on.

        Includes the resume id and its text, so swapping the attached resume or
        uploading a new version marks the old answers stale.
        """
        parts = [
            application.company_name,
            application.job_title,
            application.job_description or "",
            str(application.resume_id or ""),
        ]

        if application.resume_id is not None:
            resume = self.db.execute(
                select(Resume.extracted_text).where(Resume.id == application.resume_id)
            ).scalar_one_or_none()
            parts.append(resume or "")

        return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()

    def _shape(self, task: AITask, raw: dict | list) -> dict:
        """Force the model's answer into the shape the frontend expects.

        Models drop fields, return a bare list where an object was asked for,
        and put strings where arrays belong. Normalising once here means the UI
        never has to defend itself.
        """
        if task is AITask.JD_ANALYSIS:
            data = raw if isinstance(raw, dict) else {}
            return JDAnalysis(
                summary=str(data.get("summary") or ""),
                seniority=str(data.get("seniority") or "unclear"),
                must_have_skills=as_str_list(data.get("must_have_skills")),
                nice_to_have_skills=as_str_list(data.get("nice_to_have_skills")),
                responsibilities=as_str_list(data.get("responsibilities")),
                keywords=as_str_list(data.get("keywords")),
                watch_outs=as_str_list(data.get("watch_outs")),
            ).model_dump()

        if task is AITask.RESUME_MATCH:
            data = raw if isinstance(raw, dict) else {}
            return ResumeMatch(
                score=_clamp_score(data.get("score")),
                verdict=str(data.get("verdict") or ""),
                matched_skills=as_str_list(data.get("matched_skills")),
                missing_skills=as_str_list(data.get("missing_skills")),
                strengths=as_str_list(data.get("strengths")),
                suggestions=as_str_list(data.get("suggestions")),
            ).model_dump()

        # Interview prep. A bare list of questions is a common shape.
        data = raw if isinstance(raw, dict) else {"questions": raw}
        questions = []
        for item in data.get("questions") or []:
            if isinstance(item, str):
                questions.append({"question": item, "category": "role", "why": "", "hint": ""})
            elif isinstance(item, dict) and item.get("question"):
                questions.append(
                    {
                        "question": str(item["question"]),
                        "category": str(item.get("category") or "role"),
                        "why": str(item.get("why") or ""),
                        "hint": str(item.get("hint") or ""),
                    }
                )

        return InterviewPrep(
            questions=questions[:20],  # type: ignore[arg-type]
            questions_to_ask=as_str_list(data.get("questions_to_ask")),
        ).model_dump()


def _clamp_score(value: object) -> int:
    """Models return "85", "85%", 8.5 and occasionally nonsense."""
    try:
        if isinstance(value, str):
            value = value.strip().rstrip("%")
        number = int(round(float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, number))


def _applicant_name(application: Application) -> str:
    user = application.user
    name = " ".join(filter(None, [user.first_name, user.last_name])).strip()
    return name or "the applicant"


def ai_status(provider: AIProvider) -> tuple[bool, str, str]:
    """Whether generation will work, and a sentence explaining if not.

    Reports the provider actually wired in rather than the setting, so the two
    can never disagree.
    """
    if provider.name == "mock":
        return True, "mock", "Using canned responses — no model is being called."
    if provider.name == "gemini" and not settings.GEMINI_API_KEY.strip():
        return False, "gemini", "AI is not set up. Add a GEMINI_API_KEY to enable it."
    return True, provider.name, "Ready."
