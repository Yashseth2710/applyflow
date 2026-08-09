"""Prompt templates.

Each opens with a TASK line. It focuses the model, and it is what the mock
provider keys off so tests never need a network.
"""

from enum import Enum


class AITask(str, Enum):
    JD_ANALYSIS = "jd_analysis"
    RESUME_MATCH = "resume_match"
    COVER_LETTER = "cover_letter"
    INTERVIEW_QUESTIONS = "interview_questions"


#: Trimming keeps us inside the token budget and stops one enormous paste from
#: burning the daily quota. Resumes and descriptions are front-loaded anyway.
MAX_JD_CHARS = 8000
MAX_RESUME_CHARS = 8000

#: Output budget per task.
#:
#: Generous because a reasoning model spends this budget on thinking before it
#: writes anything — one measured run used 1238 thinking tokens against 806 of
#: answer, and truncated. These are ceilings, not targets: unused budget costs
#: nothing, whereas a cut-off answer is a failed request.
MAX_OUTPUT_TOKENS: dict[str, int] = {
    AITask.JD_ANALYSIS.value: 4000,
    AITask.RESUME_MATCH.value: 6000,
    AITask.INTERVIEW_QUESTIONS.value: 10000,
    AITask.COVER_LETTER.value: 4000,
}


def _clip(text: str | None, limit: int) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "\n[trimmed]"


JSON_RULES = (
    "Reply with JSON only. No commentary, no markdown fences. "
    "If something is not stated, omit it rather than inventing it."
)


def jd_analysis(job_title: str, company: str, description: str) -> str:
    return f"""TASK: {AITask.JD_ANALYSIS.value}

Analyse this job posting for someone deciding whether to apply.

Company: {company}
Role: {job_title}

Posting:
\"\"\"
{_clip(description, MAX_JD_CHARS)}
\"\"\"

{JSON_RULES}

Shape:
{{
  "summary": "two sentences on what this job actually is",
  "seniority": "intern | junior | mid | senior | lead | unclear",
  "must_have_skills": ["..."],
  "nice_to_have_skills": ["..."],
  "responsibilities": ["..."],
  "keywords": ["terms worth mirroring in a resume"],
  "watch_outs": ["vague or concerning things in the posting, if any"]
}}"""


def resume_match(job_title: str, company: str, description: str, resume_text: str) -> str:
    return f"""TASK: {AITask.RESUME_MATCH.value}

Compare this resume against this job posting. Be specific and honest — a
generous score is useless to someone deciding where to spend their time.

Company: {company}
Role: {job_title}

Posting:
\"\"\"
{_clip(description, MAX_JD_CHARS)}
\"\"\"

Resume:
\"\"\"
{_clip(resume_text, MAX_RESUME_CHARS)}
\"\"\"

{JSON_RULES}

Shape:
{{
  "score": 0-100,
  "verdict": "one sentence on whether this is worth applying to",
  "matched_skills": ["required by the posting and evidenced in the resume"],
  "missing_skills": ["required by the posting and absent from the resume"],
  "strengths": ["what this resume argues well for this role"],
  "suggestions": ["concrete edits to the resume for this application"]
}}"""


def cover_letter(
    job_title: str,
    company: str,
    description: str,
    resume_text: str,
    applicant_name: str,
) -> str:
    return f"""TASK: {AITask.COVER_LETTER.value}

Draft a cover letter for this application.

Rules:
- Around 250 words, three or four short paragraphs.
- Plain, direct language. No "I am writing to express my keen interest".
- Use only facts present in the resume. Never invent experience or numbers.
- No placeholders like [Company] — the details are all below.
- Return the letter body only: no addresses, no date, no subject line.

Applicant: {applicant_name}
Company: {company}
Role: {job_title}

Posting:
\"\"\"
{_clip(description, MAX_JD_CHARS)}
\"\"\"

Resume:
\"\"\"
{_clip(resume_text, MAX_RESUME_CHARS)}
\"\"\"

Reply with the letter text only."""


def interview_questions(job_title: str, company: str, description: str) -> str:
    return f"""TASK: {AITask.INTERVIEW_QUESTIONS.value}

List the questions this candidate should prepare for.

Company: {company}
Role: {job_title}

Posting:
\"\"\"
{_clip(description, MAX_JD_CHARS)}
\"\"\"

{JSON_RULES}

Shape:
{{
  "questions": [
    {{
      "question": "the question as it would be asked",
      "category": "technical | behavioural | role | company",
      "why": "why this posting makes it likely",
      "hint": "what a strong answer covers"
    }}
  ],
  "questions_to_ask": ["good questions for the candidate to ask them"]
}}

Give 8 to 12 questions weighted towards what this posting emphasises."""
