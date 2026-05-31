"""Political event corpus ingestion — tweets, truths, and speech transcripts."""

from quant.events.schema import EventRecord
from quant.events.store import append_event_jsonl, iter_events_jsonl

__all__ = ["EventRecord", "append_event_jsonl", "iter_events_jsonl"]
