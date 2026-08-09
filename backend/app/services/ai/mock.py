"""Deterministic provider used by tests and by default.

Answers are shaped exactly like a real model's, so everything above this — the
parser, the caching, the endpoints, the UI — is exercised without a network.
That keeps CI fast and stops the suite failing when a quota runs out.
"""

import hashlib
import json

from app.services.ai.base import AIProvider, Generation
from app.services.ai.prompts import AITask


class MockProvider(AIProvider):
    name = "mock"

    def generate(self, prompt: str, *, fast: bool = False, max_tokens: int = 2048) -> Generation:
        task = _task_of(prompt)
        # Seeded from the prompt so the same input always gives the same answer,
        # which is what makes cache behaviour testable.
        seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)

        if task is AITask.COVER_LETTER:
            return Generation(text=_cover_letter(), model="mock")

        if task is AITask.RESUME_MATCH:
            payload = {
                "score": seed % 101,
                "verdict": "Worth applying to, with a few resume tweaks.",
                "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
                "missing_skills": ["Kubernetes"],
                "strengths": ["Backend depth", "Shipped and maintained a real service"],
                "suggestions": ["Lead with the API work", "Name the database explicitly"],
            }
        elif task is AITask.INTERVIEW_QUESTIONS:
            payload = {
                "questions": [
                    {
                        "question": "Walk me through a service you designed end to end.",
                        "category": "technical",
                        "why": "The posting stresses ownership of backend services.",
                        "hint": "Cover the data model, the trade-offs, and what you would change.",
                    },
                    {
                        "question": "Tell me about a time a deploy went wrong.",
                        "category": "behavioural",
                        "why": "They mention on-call rotation.",
                        "hint": "Be concrete about detection, the fix, and the follow-up.",
                    },
                ],
                "questions_to_ask": [
                    "How is on-call shared across the team?",
                    "What does the first ninety days look like?",
                ],
            }
        else:
            payload = {
                "summary": "A backend role focused on building and running Python services.",
                "seniority": "mid",
                "must_have_skills": ["Python", "FastAPI", "PostgreSQL"],
                "nice_to_have_skills": ["Docker", "AWS"],
                "responsibilities": ["Build and maintain APIs", "Own services in production"],
                "keywords": ["REST", "SQL", "CI"],
                "watch_outs": ["The posting does not mention team size."],
            }

        return Generation(text=json.dumps(payload), model="mock")


def _task_of(prompt: str) -> AITask:
    first = prompt.strip().splitlines()[0] if prompt.strip() else ""
    for task in AITask:
        if task.value in first:
            return task
    return AITask.JD_ANALYSIS


def _cover_letter() -> str:
    return (
        "I am applying for the backend engineer role. I have spent the last "
        "three years building Python services, most recently an application "
        "tracker that handles authentication, file storage and a REST API used "
        "daily.\n\n"
        "Your posting stresses ownership of services in production. In my last "
        "role I designed the schema, wrote the migrations and stayed on call "
        "for what I shipped, which taught me more about sensible defaults than "
        "any amount of design review.\n\n"
        "I would welcome the chance to talk about how I could help."
    )
