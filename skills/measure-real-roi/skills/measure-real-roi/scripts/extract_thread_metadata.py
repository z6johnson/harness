#!/usr/bin/env python3
"""Extract metadata-only thread activity from TritonAI Harness session logs."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


TOP_LEVEL_TYPE_RE = re.compile(r'^\{"timestamp"\s*:\s*"[^"]+"\s*,\s*"type"\s*:\s*"([^"]+)"')
ALLOWED_EVENT_TYPES = {"task_started", "task_complete"}


@dataclass(frozen=True)
class TurnInterval:
    thread_ref: str
    start: datetime
    end: datetime
    turn_id: str


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def top_level_type(line: str) -> str | None:
    match = TOP_LEVEL_TYPE_RE.search(line.rstrip())
    return match.group(1) if match else None


def shallow_json_values(line: str, wanted_paths: set[tuple[str, ...]]) -> dict[tuple[str, ...], str]:
    """Return only explicitly requested scalar paths from a JSON line."""
    values: dict[tuple[str, ...], str] = {}
    path: list[str] = []
    stack: list[str] = []
    key = ""
    value = ""
    index = 0
    length = len(line)

    def record_scalar(current_path: tuple[str, ...], scalar: str) -> None:
        if current_path in wanted_paths:
            values[current_path] = scalar

    while index < length:
        char = line[index]
        if char == "{":
            stack.append("object")
            path.append(key) if key else path.append("")
            key = ""
            index += 1
            continue
        if char == "[":
            stack.append("array")
            path.append(key) if key else path.append("")
            key = ""
            index += 1
            continue
        if char in "}]":
            if stack:
                stack.pop()
            if path:
                path.pop()
            index += 1
            continue
        if char == '"':
            index += 1
            text = []
            while index < length:
                current = line[index]
                if current == "\\" and index + 1 < length:
                    text.append(line[index + 1])
                    index += 2
                    continue
                if current == '"':
                    index += 1
                    break
                text.append(current)
                index += 1
            scalar = "".join(text)
            current_path = tuple(part for part in path if part != "")
            if stack and stack[-1] == "object" and key:
                current_path = current_path + (key,)
            record_scalar(current_path, scalar)
            if stack and stack[-1] == "object":
                key = scalar
            continue
        if char == ",":
            key = ""
            index += 1
            continue
        if char == ":":
            index += 1
            continue
        if char.isdigit() or char == "-":
            start = index
            while index < length and (line[index].isdigit() or line[index] in ".-eE+"):
                index += 1
            record_scalar(tuple(part for part in path if part != ""), line[start:index])
            continue
        if char in "tfn":
            start = index
            while index < length and line[index].isalpha():
                index += 1
            record_scalar(tuple(part for part in path if part != ""), line[start:index])
            continue
        index += 1
    return values


def load_hmac_key(args: argparse.Namespace) -> bytes:
    if args.hmac_key:
        return args.hmac_key.encode("utf-8")
    if args.hmac_key_file:
        path = Path(args.hmac_key_file).expanduser()
        return path.read_text(encoding="utf-8").strip().encode("utf-8")
    env_hmac_key = os.environ.get("REAL_ROI_THREAD_SECRET")
    if env_hmac_key:
        return env_hmac_key.encode("utf-8")
    if args.keychain_service:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", args.keychain_account, "-s", args.keychain_service, "-w"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().encode("utf-8")
    raise ValueError("Provide --secret, --secret-file, REAL_ROI_THREAD_SECRET, or --keychain-service")


def thread_ref(session_id: str, hmac_key: bytes) -> str:
    digest = hmac.new(hmac_key, session_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return "thr-" + digest[:16]


def local_date(moment: datetime, timezone_name: str) -> str:
    return moment.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def merge_intervals(intervals: list[TurnInterval], gap_cutoff: timedelta) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []
    ordered = sorted((interval.start, interval.end) for interval in intervals)
    merged: list[list[datetime]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start - merged[-1][1] <= gap_cutoff:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def allocate_overlaps(
    periods_by_thread: dict[str, list[tuple[datetime, datetime]]]
) -> dict[str, timedelta]:
    totals: dict[str, timedelta] = defaultdict(timedelta)
    boundaries: set[datetime] = set()
    for periods in periods_by_thread.values():
        for start, end in periods:
            boundaries.add(start)
            boundaries.add(end)
    ordered_boundaries = sorted(boundaries)
    for start, end in zip(ordered_boundaries, ordered_boundaries[1:]):
        active_threads = [
            thread
            for thread, periods in periods_by_thread.items()
            if any(period_start <= start and end <= period_end for period_start, period_end in periods)
        ]
        if not active_threads:
            continue
        share = (end - start) / len(active_threads)
        for thread in active_threads:
            totals[thread] += share
    return totals


def collect_intervals(
    sessions_dir: Path,
    start_date: str,
    end_date: str,
    timezone_name: str,
    gap_cutoff_minutes: int,
    hmac_key: bytes,
) -> tuple[dict[str, dict[str, object]], dict[str, list[TurnInterval]]]:
    sessions: dict[str, dict[str, object]] = {}
    intervals_by_session: dict[str, list[TurnInterval]] = defaultdict(list)
    starts: dict[str, dict[str, datetime]] = defaultdict(dict)
    local_zone = ZoneInfo(timezone_name)
    start_boundary = datetime.combine(datetime.fromisoformat(start_date).date(), time.min, tzinfo=local_zone)
    end_boundary = datetime.combine(datetime.fromisoformat(end_date).date(), time.max, tzinfo=local_zone)

    for file_path in sorted(sessions_dir.rglob("*.jsonl")):
        session_id = ""
        for line in file_path.open("r", encoding="utf-8"):
            line_type = top_level_type(line)
            if line_type == "session_meta":
                values = shallow_json_values(
                    line,
                    {("payload", "id"), ("payload", "timestamp"), ("timestamp",)},
                )
                session_id = values.get(("payload", "id"), "")
                if not session_id:
                    continue
                sessions[session_id] = {
                    "thread_ref": thread_ref(session_id, hmac_key),
                    "source_file": file_path.name,
                    "created_at": values.get(("payload", "timestamp"), values.get(("timestamp", ""))),
                }
            elif line_type == "event_msg" and session_id:
                values = shallow_json_values(
                    line,
                    {("payload", "type"), ("timestamp",), ("payload", "turn_id")},
                )
                event_type = values.get(("payload", "type"), "")
                if event_type not in ALLOWED_EVENT_TYPES:
                    continue
                timestamp = parse_timestamp(values.get(("timestamp",), ""))
                if not (start_boundary <= timestamp.astimezone(local_zone) <= end_boundary):
                    continue
                turn_id = values.get(("payload", "turn_id"), "")
                if event_type == "task_started":
                    starts[session_id][turn_id] = timestamp
                elif event_type == "task_complete" and turn_id in starts[session_id]:
                    start = starts[session_id].pop(turn_id)
                    if timestamp > start:
                        intervals_by_session[session_id].append(
                            TurnInterval(
                                thread_ref=thread_ref(session_id, hmac_key),
                                start=start,
                                end=timestamp,
                                turn_id=turn_id,
                            )
                        )
    return sessions, intervals_by_session


def derive_thread_metadata(
    sessions: dict[str, dict[str, object]],
    intervals_by_session: dict[str, list[TurnInterval]],
    timezone_name: str,
    gap_cutoff_minutes: int,
) -> list[dict[str, object]]:
    gap_cutoff = timedelta(minutes=gap_cutoff_minutes)
    periods_by_thread_date: dict[tuple[str, str], list[tuple[datetime, datetime]]] = defaultdict(list)
    turn_counts: dict[tuple[str, str], int] = defaultdict(int)
    first_activity: dict[tuple[str, str], datetime] = {}
    last_activity: dict[tuple[str, str], datetime] = {}

    for session_id, intervals in intervals_by_session.items():
        ref = str(sessions[session_id]["thread_ref"])
        by_date: dict[str, list[TurnInterval]] = defaultdict(list)
        for interval in intervals:
            date = local_date(interval.start, timezone_name)
            by_date[date].append(interval)
        for date, day_intervals in by_date.items():
            key = (ref, date)
            turn_counts[key] += len(day_intervals)
            for interval in day_intervals:
                first_activity[key] = min(first_activity.get(key, interval.start), interval.start)
                last_activity[key] = max(last_activity.get(key, interval.end), interval.end)
            periods_by_thread_date[key].extend(merge_intervals(day_intervals, gap_cutoff))

    metadata: list[dict[str, object]] = []
    dates = sorted({date for _, date in periods_by_thread_date})
    for date in dates:
        threads_for_date = {ref for ref, day in periods_by_thread_date if day == date}
        periods: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
        for ref in threads_for_date:
            periods[ref].extend(periods_by_thread_date[(ref, date)])
        allocated = allocate_overlaps(periods)
        for ref in sorted(threads_for_date):
            key = (ref, date)
            metadata.append(
                {
                    "thread_ref": ref,
                    "date": date,
                    "first_activity": first_activity[key].astimezone(ZoneInfo(timezone_name)).isoformat(),
                    "last_activity": last_activity[key].astimezone(ZoneInfo(timezone_name)).isoformat(),
                    "turn_count": turn_counts[key],
                    "derived_minutes": round(allocated[ref].total_seconds() / 60, 2),
                    "gap_cutoff_minutes": gap_cutoff_minutes,
                    "provenance": "derived",
                }
            )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-dir", default="~/.tritonai-harness/codex/sessions")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--gap-cutoff-minutes", type=int, default=10)
    parser.add_argument("--timezone", default="America/Los_Angeles")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--secret", dest="hmac_key")
    parser.add_argument("--secret-file", dest="hmac_key_file")
    parser.add_argument("--keychain-service", default="real-roi-thread-secret")
    parser.add_argument("--keychain-account", default=os.environ.get("USER", ""))
    args = parser.parse_args()

    sessions_dir = Path(args.sessions_dir).expanduser()
    if not sessions_dir.exists():
        raise SystemExit(f"Sessions directory does not exist: {sessions_dir}")
    hmac_key = load_hmac_key(args)
    sessions, intervals = collect_intervals(
        sessions_dir,
        args.start_date,
        args.end_date,
        args.timezone,
        args.gap_cutoff_minutes,
        hmac_key,
    )
    metadata = derive_thread_metadata(sessions, intervals, args.timezone, args.gap_cutoff_minutes)
    result = {
        "schema_version": "1.0",
        "start_date": args.start_date,
        "end_date": args.end_date,
        "timezone": args.timezone,
        "gap_cutoff_minutes": args.gap_cutoff_minutes,
        "thread_count": len({item["thread_ref"] for item in metadata}),
        "threads": metadata,
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
