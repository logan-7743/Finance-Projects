"""Tests for event corpus ingestion."""

from quant.events.schema import EventRecord
from quant.events.sources.trump_fm import post_to_event
from quant.events.sources.whitehouse import extract_sitemap_links


def test_post_to_event_skips_reposts_by_default() -> None:
    post = {
        "id": "ts_1",
        "platform": "truth",
        "platformId": "1",
        "content": "Hello world",
        "createdAt": "2025-01-01T12:00:00.000Z",
        "isRepost": True,
    }
    assert post_to_event(post) is None


def test_post_to_event_normalizes_truth_post() -> None:
    post = {
        "id": "ts_116667457759700602",
        "platform": "truth",
        "platformId": "116667457759700602",
        "content": "Example post text",
        "createdAt": "2026-05-31T05:08:48.410Z",
        "isRepost": False,
        "deletedAt": None,
        "externalMetrics": {"likes": 1},
    }
    event = post_to_event(post)
    assert event is not None
    assert event.event_id == "trump_fm:ts_116667457759700602"
    assert event.source == "trump_fm"
    assert event.url == "https://trump.fm/post/ts_116667457759700602"
    assert event.text == "Example post text"
    assert event.metadata["platform"] == "truth"


def test_event_record_json_roundtrip() -> None:
    from datetime import UTC, datetime

    original = EventRecord(
        event_id="trump_fm:ts_1",
        utc_timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        source="trump_fm",
        event_type="social_post",
        text="Hi",
        url="https://trump.fm/post/1",
        native_id="ts_1",
        metadata={"platform": "truth"},
    )
    restored = EventRecord.from_json_dict(original.to_json_dict())
    assert restored == original


def test_whitehouse_sitemap_links_filter_to_window() -> None:
    from datetime import UTC, datetime

    xml = """
    <urlset>
      <url><loc>https://www.whitehouse.gov/briefings-statements/2024/04/old-post/</loc></url>
      <url><loc>https://www.whitehouse.gov/briefings-statements/2024/05/in-window/</loc></url>
      <url><loc>https://www.whitehouse.gov/remarks/2025/01/the-inaugural-address/</loc></url>
      <url><loc>https://www.whitehouse.gov/news/2025/01/not-an-event-source/</loc></url>
    </urlset>
    """

    links = extract_sitemap_links(xml, since=datetime(2024, 5, 31, tzinfo=UTC))

    assert links == [
        "https://www.whitehouse.gov/briefings-statements/2024/05/in-window/",
        "https://www.whitehouse.gov/remarks/2025/01/the-inaugural-address/",
    ]
