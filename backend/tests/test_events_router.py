"""Tests for the local event corpus API."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from quant.events.paths import normalized_path
from quant.events.schema import EventRecord
from quant.events.store import append_event_jsonl


def test_events_api_lists_local_corpus(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EVENTS_DATA_DIR", str(tmp_path))
    path = normalized_path("trump_events.jsonl")
    append_event_jsonl(
        path,
        EventRecord(
            event_id="trump_fm:ts_1",
            utc_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            source="trump_fm",
            event_type="social_post",
            text="Tariff post mentioning autos",
            url="https://trump.fm/post/ts_1",
            native_id="ts_1",
            metadata={"platform": "truth"},
        ),
    )
    append_event_jsonl(
        path,
        EventRecord(
            event_id="whitehouse:test",
            utc_timestamp=datetime(2025, 1, 20, 22, 0, tzinfo=UTC),
            source="whitehouse",
            event_type="speech_transcript",
            text="Official transcript text",
            url="https://www.whitehouse.gov/remarks/test/",
            native_id="test",
            metadata={"title": "Test Remarks"},
        ),
    )

    client = TestClient(app)
    response = client.get("/api/events/trump", params={"q": "tariff", "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["count"] == 2
    assert payload["total_matching"] == 1
    assert payload["events"][0]["event_id"] == "trump_fm:ts_1"


def test_events_api_validates_date_bounds(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EVENTS_DATA_DIR", str(tmp_path))
    client = TestClient(app)

    response = client.get("/api/events/trump", params={"from": "not-a-date"})

    assert response.status_code == 400
    assert "ISO date" in response.json()["detail"]
