"""CLI for pulling the Trump event corpus."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

from quant.events.manifest import write_manifest
from quant.events.paths import events_data_root, manifest_path, normalized_path
from quant.events.report import merge_jsonl_files, summarize_jsonl
from quant.events.sources.trump_fm import pull_trump_fm
from quant.events.sources.whitehouse import pull_whitehouse


def default_since() -> datetime:
    return datetime.now(tz=UTC) - timedelta(days=365 * 2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull Trump tweets/truths and speech transcripts.")
    parser.add_argument(
        "--source",
        choices=("all", "trump_fm", "whitehouse"),
        default="all",
        help="Which source to pull (default: all).",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="ISO date/datetime cutoff (default: 2 years ago, UTC).",
    )
    parser.add_argument(
        "--until",
        default=None,
        help="ISO date/datetime upper bound (default: now, UTC).",
    )
    parser.add_argument(
        "--include-reposts",
        action="store_true",
        help="Include reposts from trump.fm (default: skip).",
    )
    return parser.parse_args()


def parse_bound(value: str | None, fallback: datetime) -> datetime:
    if value is None:
        return fallback.astimezone(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(UTC)


def main() -> None:
    args = parse_args()
    since = parse_bound(args.since, default_since())
    until = parse_bound(args.until, datetime.now(tz=UTC))

    events_data_root().mkdir(parents=True, exist_ok=True)
    pull_stats: dict[str, object] = {"since": since.isoformat(), "until": until.isoformat()}

    if args.source in ("all", "trump_fm"):
        print(f"Pulling trump.fm social posts since {since.date()} ...")
        pull_stats["trump_fm"] = pull_trump_fm(
            since=since,
            until=until,
            include_reposts=args.include_reposts,
        )
        print(pull_stats["trump_fm"])

    if args.source in ("all", "whitehouse"):
        print(f"Pulling White House remarks/briefings since {since.date()} ...")
        pull_stats["whitehouse"] = pull_whitehouse(since=since, until=until)
        print(pull_stats["whitehouse"])

    social_path = normalized_path("trump_social.jsonl")
    speech_path = normalized_path("trump_speeches.jsonl")
    merged_path = normalized_path("trump_events.jsonl")

    merge_result = merge_jsonl_files([social_path, speech_path], merged_path)
    pull_stats["merge"] = merge_result
    pull_stats["summaries"] = {
        "social": summarize_jsonl(social_path),
        "speeches": summarize_jsonl(speech_path),
        "merged": summarize_jsonl(merged_path),
    }

    write_manifest(manifest_path(), pull_stats)

    print("\n=== Coverage ===")
    for label, summary in pull_stats["summaries"].items():  # type: ignore[index]
        print(f"{label}: {summary}")


if __name__ == "__main__":
    main()
