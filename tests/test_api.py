import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import tempfile

os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["NEUROVERSE_DB"] = os.path.join(tempfile.gettempdir(), "neuroverse_test.db")

import pytest
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db():
    from backend import database

    if os.path.exists(os.environ["NEUROVERSE_DB"]):
        os.remove(os.environ["NEUROVERSE_DB"])
    database.init_db()
    yield


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["llm_enabled"] is False


def test_achievements_catalog():
    r = client.get("/api/achievements")
    assert r.status_code == 200
    data = r.json()
    assert "mission_complete" in data
    assert "name" in data["mission_complete"]


def test_full_playthrough():
    r = client.post("/api/adventure", json={"idea": "dinosaur world", "player": "Maha"})
    assert r.status_code == 200
    state = r.json()
    assert state["chapter"] == 1
    assert state["traits"] == {"bravery": 0, "curiosity": 0, "kindness": 0}
    assert "first_light" in state["achievements"]
    assert state["new_achievements"] == ["first_light"]
    session_id = state["session_id"]

    r2 = client.get("/api/sessions")
    assert any(s["session_id"] == session_id for s in r2.json())

    r3 = client.post("/api/choice", json={"session_id": session_id, "choice": state["choices"][0]})
    assert r3.status_code == 200
    assert r3.json()["chapter"] == 2

    r4 = client.get(f"/api/session/{session_id}")
    assert r4.status_code == 200
    assert r4.json()["chapter"] == 2
    assert "inventory" in r4.json()


def test_choice_on_missing_session_returns_404():
    r = client.post("/api/choice", json={"session_id": "does-not-exist", "choice": "Explore"})
    assert r.status_code == 404


def test_delete_session():
    r = client.post("/api/adventure", json={"idea": "space", "player": "Maha"})
    session_id = r.json()["session_id"]
    d = client.delete(f"/api/session/{session_id}")
    assert d.status_code == 200
    r2 = client.get(f"/api/session/{session_id}")
    assert r2.status_code == 404
