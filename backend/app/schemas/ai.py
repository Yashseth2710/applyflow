"""AI request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.prompts import AITask


class AIStatus(BaseModel):
    """Whether AI is usable, so the UI can explain itself instead of failing."""

    enabled: bool
    provider: str
    detail: str


class JDAnalysis(BaseModel):
    summary: str = ""
    seniority: str = "unclear"
    must_have_skills: list[str] = []
    nice_to_have_skills: list[str] = []
    responsibilities: list[str] = []
    keywords: list[str] = []
    watch_outs: list[str] = []


class ResumeMatch(BaseModel):
    score: int = Field(default=0, ge=0, le=100)
    verdict: str = ""
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    strengths: list[str] = []
    suggestions: list[str] = []


class InterviewQuestion(BaseModel):
    question: str
    category: str = "role"
    why: str = ""
    hint: str = ""


class InterviewPrep(BaseModel):
    questions: list[InterviewQuestion] = []
    questions_to_ask: list[str] = []


class AIOutputResponse(BaseModel):
    """One cached generation.

    The result is carried in a field typed for its task rather than an untyped
    blob. The database stores JSON, but the API describes exactly what each task
    produces, so the client gets real types instead of casting a dictionary.

    `stale` means the job description or resume changed after this was written,
    so it describes text that no longer exists. Shown rather than deleted — an
    old answer with a warning beats no answer.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    task: AITask

    analysis: JDAnalysis | None = None
    match: ResumeMatch | None = None
    prep: InterviewPrep | None = None
    text: str | None = None

    model: str
    provider: str
    generated_at: datetime
    stale: bool = False

    @classmethod
    def from_output(cls, output: object) -> "AIOutputResponse":
        """Map a stored row onto the field its task belongs in."""
        task: AITask = output.task  # type: ignore[attr-defined]
        content: dict | None = output.content  # type: ignore[attr-defined]

        return cls(
            id=output.id,  # type: ignore[attr-defined]
            application_id=output.application_id,  # type: ignore[attr-defined]
            task=task,
            analysis=JDAnalysis(**content) if task is AITask.JD_ANALYSIS and content else None,
            match=ResumeMatch(**content) if task is AITask.RESUME_MATCH and content else None,
            prep=InterviewPrep(**content)
            if task is AITask.INTERVIEW_QUESTIONS and content
            else None,
            text=output.text,  # type: ignore[attr-defined]
            model=output.model,  # type: ignore[attr-defined]
            provider=output.provider,  # type: ignore[attr-defined]
            generated_at=output.generated_at,  # type: ignore[attr-defined]
            stale=getattr(output, "stale", False),
        )


class AIOutputList(BaseModel):
    items: list[AIOutputResponse]
