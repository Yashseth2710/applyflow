"""AI generation, caching, staleness, and surviving bad model output."""

import pytest
from fastapi.testclient import TestClient

from app.services.ai import AIBadOutput, MockProvider, as_str_list, parse_json
from app.services.ai.base import Generation

JOB_DESCRIPTION = (
    "We are hiring a backend engineer to build and run Python services. "
    "You will own APIs end to end, work with PostgreSQL and FastAPI, and share "
    "an on-call rotation. Docker and AWS experience is a plus. Three or more "
    "years of professional experience is expected for this role."
)


def create_application(client: TestClient, user: dict, **extra: object) -> dict:
    r = client.post(
        "/api/v1/applications",
        headers=user["headers"],
        json={
            "company_name": "Globex",
            "job_title": "Backend Engineer",
            "job_description": JOB_DESCRIPTION,
            **extra,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def generate(client: TestClient, user: dict, application_id: str, task: str, force: bool = False):
    return client.post(
        f"/api/v1/ai/applications/{application_id}/{task}?force={str(force).lower()}",
        headers=user["headers"],
    )


# ---- the JSON parser, which is where model output actually breaks ----


def test_parses_plain_json():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_parses_json_inside_a_markdown_fence():
    """Models fence their output constantly, whatever the prompt says."""
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('```\n{"a": 1}\n```') == {"a": 1}


def test_parses_json_wrapped_in_prose():
    text = 'Sure! Here is the analysis:\n{"a": 1}\nHope that helps.'
    assert parse_json(text) == {"a": 1}


def test_repairs_trailing_commas():
    """The single most common malformation."""
    assert parse_json('{"a": [1, 2,],}') == {"a": [1, 2]}


def test_parses_a_bare_array():
    assert parse_json('["Python", "SQL"]') == ["Python", "SQL"]


@pytest.mark.parametrize("text", ["", "   ", "I cannot help with that.", "{broken"])
def test_unusable_output_raises_rather_than_crashing(text):
    with pytest.raises(AIBadOutput):
        parse_json(text)


def test_string_lists_survive_the_shapes_models_actually_return():
    assert as_str_list(["Python", " SQL "]) == ["Python", "SQL"]
    assert as_str_list("Python") == ["Python"]
    assert as_str_list([{"name": "Python"}, {"skill": "SQL"}]) == ["Python", "SQL"]
    assert as_str_list(None) == []
    assert as_str_list([1, 2, None]) == []


# ---- status ----


def test_status_reports_the_provider(client, registered_user):
    r = client.get("/api/v1/ai/status", headers=registered_user["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "mock"
    assert body["enabled"] is True


def test_ai_requires_authentication(client):
    assert client.get("/api/v1/ai/status").status_code == 401


# ---- generating ----


def test_job_description_analysis(client, registered_user):
    application = create_application(client, registered_user)

    r = generate(client, registered_user, application["id"], "jd_analysis")
    assert r.status_code == 201 or r.status_code == 200, r.text

    body = r.json()
    assert body["task"] == "jd_analysis"
    assert body["provider"] == "mock"
    # Typed per task rather than an untyped blob, so the client needs no casts.
    analysis = body["analysis"]
    assert analysis["summary"]
    assert "Python" in analysis["must_have_skills"]
    assert body["match"] is None
    assert body["stale"] is False


def test_interview_questions(client, registered_user):
    application = create_application(client, registered_user)

    body = generate(client, registered_user, application["id"], "interview_questions").json()
    questions = body["prep"]["questions"]
    assert len(questions) >= 1
    assert questions[0]["question"]
    assert questions[0]["category"]


def test_analysis_without_a_job_description_is_refused(client, registered_user):
    """Nothing to analyse — a clear message beats a confident hallucination."""
    application = create_application(client, registered_user, job_description=None)

    r = generate(client, registered_user, application["id"], "jd_analysis")
    assert r.status_code == 422
    assert "job description" in r.json()["detail"].lower()


def test_match_without_a_resume_is_refused(client, registered_user):
    application = create_application(client, registered_user)

    r = generate(client, registered_user, application["id"], "resume_match")
    assert r.status_code == 422
    assert "resume" in r.json()["detail"].lower()


def test_unknown_task_is_rejected(client, registered_user):
    application = create_application(client, registered_user)
    r = generate(client, registered_user, application["id"], "make_me_a_sandwich")
    assert r.status_code == 422


# ---- caching ----


def test_a_second_request_reuses_the_stored_answer(client, registered_user):
    """Generations cost seconds and quota, so repeat views must not regenerate."""
    application = create_application(client, registered_user)

    first = generate(client, registered_user, application["id"], "jd_analysis").json()
    second = generate(client, registered_user, application["id"], "jd_analysis").json()

    assert first["id"] == second["id"]
    assert first["generated_at"] == second["generated_at"]


def test_force_regenerates(client, registered_user):
    application = create_application(client, registered_user)

    first = generate(client, registered_user, application["id"], "jd_analysis").json()
    forced = generate(client, registered_user, application["id"], "jd_analysis", force=True).json()

    # Same row, rewritten in place, so there is only ever one per task.
    assert first["id"] == forced["id"]
    assert forced["generated_at"] >= first["generated_at"]


def test_changing_the_job_description_marks_the_answer_stale(client, registered_user):
    """The cached answer describes text that no longer exists."""
    application = create_application(client, registered_user)
    generate(client, registered_user, application["id"], "jd_analysis")

    client.patch(
        f"/api/v1/applications/{application['id']}",
        headers=registered_user["headers"],
        json={"job_description": JOB_DESCRIPTION + " We also use Kubernetes heavily."},
    )

    listed = client.get(
        f"/api/v1/ai/applications/{application['id']}", headers=registered_user["headers"]
    ).json()
    assert listed["items"][0]["stale"] is True


def test_regenerating_after_a_change_clears_stale(client, registered_user):
    application = create_application(client, registered_user)
    generate(client, registered_user, application["id"], "jd_analysis")

    client.patch(
        f"/api/v1/applications/{application['id']}",
        headers=registered_user["headers"],
        json={"job_description": JOB_DESCRIPTION + " Kubernetes too."},
    )
    refreshed = generate(client, registered_user, application["id"], "jd_analysis").json()
    assert refreshed["stale"] is False


def test_listing_returns_everything_generated(client, registered_user):
    application = create_application(client, registered_user)
    generate(client, registered_user, application["id"], "jd_analysis")
    generate(client, registered_user, application["id"], "interview_questions")

    listed = client.get(
        f"/api/v1/ai/applications/{application['id']}", headers=registered_user["headers"]
    ).json()
    assert {item["task"] for item in listed["items"]} == {"jd_analysis", "interview_questions"}


def test_deleting_an_application_removes_its_generations(client, registered_user):
    application = create_application(client, registered_user)
    generate(client, registered_user, application["id"], "jd_analysis")

    client.delete(f"/api/v1/applications/{application['id']}", headers=registered_user["headers"])

    r = client.get(
        f"/api/v1/ai/applications/{application['id']}", headers=registered_user["headers"]
    )
    assert r.status_code == 404


# ---- access control ----


def test_another_user_cannot_generate_for_your_application(client, registered_user, other_user):
    application = create_application(client, registered_user)

    r = generate(client, other_user, application["id"], "jd_analysis")
    assert r.status_code == 404


def test_another_user_cannot_read_your_generations(client, registered_user, other_user):
    application = create_application(client, registered_user)
    generate(client, registered_user, application["id"], "jd_analysis")

    r = client.get(f"/api/v1/ai/applications/{application['id']}", headers=other_user["headers"])
    assert r.status_code == 404


# ---- the mock provider itself ----


def test_mock_is_deterministic():
    """Cache behaviour is only testable if the same prompt gives the same answer."""
    provider = MockProvider()
    prompt = "TASK: resume_match\nsome content"
    assert provider.generate(prompt).text == provider.generate(prompt).text


def test_mock_answers_each_task_in_its_own_shape():
    provider = MockProvider()

    analysis = parse_json(provider.generate("TASK: jd_analysis\n").text)
    assert "must_have_skills" in analysis

    match = parse_json(provider.generate("TASK: resume_match\n").text)
    assert 0 <= match["score"] <= 100

    letter = provider.generate("TASK: cover_letter\n")
    assert isinstance(letter, Generation)
    assert len(letter.text) > 100
