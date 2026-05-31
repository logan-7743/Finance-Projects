from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from quant.events.paths import manifest_path, normalized_path
from quant.events.report import summarize_jsonl
from quant.events.schema import EventRecord
from quant.events.store import iter_events_jsonl

router = APIRouter()

EventSource = Literal["all", "trump_fm", "whitehouse"]


class EventSummaryResponse(BaseModel):
    exists: bool
    count: int
    by_source: dict[str, int] = Field(default_factory=dict)
    by_month: dict[str, int] = Field(default_factory=dict)
    oldest: str | None = None
    newest: str | None = None
    manifest_updated_at: str | None = None


class EventRecordResponse(BaseModel):
    event_id: str
    utc_timestamp: str
    source: str
    event_type: str
    text: str
    url: str | None
    native_id: str
    metadata: dict[str, Any]


class EventListResponse(BaseModel):
    summary: EventSummaryResponse
    events: list[EventRecordResponse]
    total_matching: int
    limit: int
    offset: int
    has_more: bool


def _parse_bound(value: str | None, *, param_name: str) -> datetime | None:
    if value is None or value.strip() == "":
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{param_name} must be an ISO date or datetime.",
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _response_from_record(record: EventRecord) -> EventRecordResponse:
    return EventRecordResponse(
        event_id=record.event_id,
        utc_timestamp=record.utc_timestamp.astimezone(UTC).isoformat(),
        source=record.source,
        event_type=record.event_type,
        text=record.text,
        url=record.url,
        native_id=record.native_id,
        metadata=record.metadata,
    )


def _summary_response() -> EventSummaryResponse:
    summary = summarize_jsonl(normalized_path("trump_events.jsonl"))
    manifest = {}
    manifest_file = manifest_path()
    if manifest_file.exists():
        try:
            import json

            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = {}

    return EventSummaryResponse(
        exists=bool(summary.get("exists")),
        count=int(summary.get("count") or 0),
        by_source={str(k): int(v) for k, v in dict(summary.get("by_source") or {}).items()},
        by_month={str(k): int(v) for k, v in dict(summary.get("by_month") or {}).items()},
        oldest=summary.get("oldest") if isinstance(summary.get("oldest"), str) else None,
        newest=summary.get("newest") if isinstance(summary.get("newest"), str) else None,
        manifest_updated_at=manifest.get("updated_at") if isinstance(manifest.get("updated_at"), str) else None,
    )


@router.get("/trump", response_model=EventListResponse)
async def list_trump_events(
    source: Annotated[EventSource, Query()] = "all",
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    from_ts: Annotated[str | None, Query(alias="from")] = None,
    to_ts: Annotated[str | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventListResponse:
    start = _parse_bound(from_ts, param_name="from")
    end = _parse_bound(to_ts, param_name="to")
    query = q.lower().strip() if q else None

    path = normalized_path("trump_events.jsonl")
    if not path.exists():
        return EventListResponse(
            summary=_summary_response(),
            events=[],
            total_matching=0,
            limit=limit,
            offset=offset,
            has_more=False,
        )

    matches: list[EventRecord] = []
    total_matching = 0
    for record in iter_events_jsonl(path):
        if source != "all" and record.source != source:
            continue
        if start and record.utc_timestamp < start:
            continue
        if end and record.utc_timestamp > end:
            continue
        if query:
            haystack = f"{record.text} {record.metadata.get('title', '')}".lower()
            if query not in haystack:
                continue
        total_matching += 1
        matches.append(record)

    matches.sort(key=lambda event: event.utc_timestamp, reverse=True)
    page = matches[offset : offset + limit]

    return EventListResponse(
        summary=_summary_response(),
        events=[_response_from_record(record) for record in page],
        total_matching=total_matching,
        limit=limit,
        offset=offset,
        has_more=offset + limit < total_matching,
    )
