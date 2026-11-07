import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.catalog import load_catalog
from backend.main import app
from backend.models import Program

client = TestClient(app)


def test_health_reports_loaded_catalog():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["program_count"] == 3
    assert body["catalog_checked_at"] == "2026-11-05"


def test_overview_counts_programs_sources_and_verified_facts():
    response = client.get("/api/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["program_count"] == 3
    assert body["official_source_count"] == 4
    assert body["verified_fact_count"] == 15


def test_search_finds_ai_programs():
    response = client.get("/api/programs", params={"q": "artificial intelligence"})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert "utoronto-mscac-ai" in ids
    assert "uwaterloo-mmath-cs" in ids


def test_province_filter_is_case_insensitive():
    response = client.get("/api/programs", params={"province": "ontario"})
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {"utoronto-mscac-ai", "uwaterloo-mmath-cs"}


def test_unknown_tuition_is_explicit_not_guessed():
    response = client.get("/api/programs/uwaterloo-mmath-cs")
    assert response.status_code == 200
    tuition = next(
        fact for fact in response.json()["facts"] if fact["id"] == "tuition"
    )
    assert tuition["status"] == "not_collected"
    assert tuition["value"] is None


def test_program_duration_and_delivery_have_verified_citations():
    response = client.get("/api/programs")
    assert response.status_code == 200
    for program in response.json()["items"]:
        source_ids = {source["id"] for source in program["sources"]}
        for attribute in ("duration", "delivery"):
            value = program[attribute]
            if value is None:
                continue
            fact = next(item for item in program["facts"] if item["id"] == attribute)
            assert fact["status"] == "verified"
            assert fact["value"] == value
            assert fact["source_id"] in source_ids


def test_compare_returns_requested_order():
    response = client.get(
        "/api/compare",
        params={"ids": "ubc-msc-cs,utoronto-mscac-ai"},
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        "ubc-msc-cs",
        "utoronto-mscac-ai",
    ]


def test_compare_rejects_one_program_and_duplicate_ids():
    one_program = client.get("/api/compare", params={"ids": "ubc-msc-cs"})
    duplicate_program = client.get(
        "/api/compare", params={"ids": "ubc-msc-cs,ubc-msc-cs"}
    )
    assert one_program.status_code == 422
    assert duplicate_program.status_code == 422


def test_unknown_program_returns_404():
    response = client.get("/api/programs/not-a-real-program")
    assert response.status_code == 404


def test_every_verified_fact_has_a_resolvable_official_source():
    response = client.get("/api/programs")
    assert response.status_code == 200
    for program in response.json()["items"]:
        source_ids = {source["id"] for source in program["sources"]}
        for fact in program["facts"]:
            if fact["status"] == "verified":
                assert fact["value"]
                assert fact["source_id"] in source_ids


def test_program_rejects_duration_without_matching_verified_fact():
    program = next(
        item for item in load_catalog().programs if item.id == "uwaterloo-mmath-cs"
    )
    raw = program.model_dump(mode="json")
    raw["facts"] = [fact for fact in raw["facts"] if fact["id"] != "duration"]

    with pytest.raises(ValidationError, match="duration must match a verified fact"):
        Program.model_validate(raw)
