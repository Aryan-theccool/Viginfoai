"""API integration tests (SQLite in-memory, heuristic engine)."""
import os

TEST_DB = "/tmp/viginfo_test.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["AUTO_SEED"] = "false"
os.environ["OPENAI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_manual_ingest_creates_finding_and_audit():
    r = client.post("/api/ingest/manual", json={
        "title": "Test pump incident",
        "text": "The infusion pump malfunction caused over-infusion and the patient experienced hypotension requiring intervention.",
        "source_type": "Manual",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["records_created"] == 1
    finding_id = body["finding_ids"][0]

    f = client.get(f"/api/findings/{finding_id}")
    assert f.status_code == 200
    assert f.json()["category"] == "Safety Signal"
    assert f.json()["review_status"] == "PENDING"

    audit = client.get("/api/audit", params={"finding_id": finding_id})
    assert audit.status_code == 200
    actions = {e["action"] for e in audit.json()}
    assert {"CREATE", "AI_EXTRACT"} <= actions


def test_review_workflow_and_audit_immutability():
    ingest = client.post("/api/ingest/manual", json={
        "title": "Review me",
        "text": "A randomized trial showed 99% sensitivity and improved outcomes versus control (p < 0.001).",
        "source_type": "Manual",
    })
    finding_id = ingest.json()["finding_ids"][0]

    rev = client.post("/api/reviews", json={
        "finding_id": finding_id,
        "reviewer_email": "qa@example.com",
        "status": "APPROVED",
        "reviewer_notes": "Confirmed for CER inclusion.",
    })
    assert rev.status_code == 201, rev.text

    f = client.get(f"/api/findings/{finding_id}")
    assert f.json()["review_status"] == "APPROVED"

    # Override path requires a category
    bad = client.post("/api/reviews", json={
        "finding_id": finding_id, "reviewer_email": "qa@example.com", "status": "MODIFIED",
    })
    assert bad.status_code == 422

    audit = client.get("/api/audit", params={"finding_id": finding_id})
    actions = [e["action"] for e in audit.json()]
    assert "REVIEW_SUBMIT" in actions


def test_stats():
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert r.json()["findings"] >= 2
