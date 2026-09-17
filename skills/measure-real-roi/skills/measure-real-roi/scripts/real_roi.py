#!/usr/bin/env python3
"""Local Real ROI pilot collection and reporting helper."""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from extract_thread_metadata import (
    collect_intervals,
    derive_thread_metadata,
    load_thread_secret,
)


SCHEMA_VERSION = "1.1"
PROHIBITED_FIELDS = {
    "name",
    "email",
    "message",
    "content",
    "attachment",
    "file_path",
    "raw_session_id",
    "hostname",
}

WORK_TYPE_LABELS = {
    "Data analysis": "Analysis or metrics",
    "Writing": "Writing or communication",
    "Code": "Code or technical work",
    "Review": "Review or feedback",
    "Planning": "Planning or admin",
}

BASELINE_CHOICES = [
    ("I would have done it myself the old way", "manual"),
    ("I would have used another tool", "other_tool"),
    ("I would have asked someone else", "someone_else"),
    ("I would not have done it at all", "would_not_have_done"),
    ("I'm not sure", "unknown"),
]


def pilot_root(config_path: Path) -> Path:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return config_path.parent


def load_config(config_path: Path) -> dict[str, object]:
    return json.loads(config_path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def week_dates(config: dict[str, object], week: int) -> tuple[date, date]:
    start = date.fromisoformat(str(config["pilot_start_date"]))
    end = date.fromisoformat(str(config["pilot_end_date"]))
    week_start = start + timedelta(days=7 * (week - 1))
    week_end = min(week_start + timedelta(days=6), end)
    if week_start > end:
        raise ValueError(f"Week {week} is outside the pilot window")
    return week_start, week_end


def prompt_text(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("Type an answer. Blank input is not supported.")


def parse_duration(value: str) -> float | None:
    value = value.strip().lower()
    if not value or value in {"dk", "idk", "i don't know", "unknown", "not sure", "?"}:
        return None
    if value in {"none", "no", "zero", "0"}:
        return 0.0
    clock_match = re.fullmatch(r"(?:(\d+):)?(\d{1,2})", value)
    if clock_match:
        hours = float(clock_match.group(1) or 0)
        minutes = float(clock_match.group(2))
        return hours * 60 + minutes
    hour_minute_match = re.fullmatch(
        r"(?:(\d+(?:\.\d+)?)\s*h(?:ours?)?\s*)?(?:(\d+(?:\.\d+)?)\s*m(?:in(?:utes?)?|s)?)?",
        value,
    )
    if hour_minute_match and (hour_minute_match.group(1) or hour_minute_match.group(2)):
        hours = float(hour_minute_match.group(1) or 0)
        minutes = float(hour_minute_match.group(2) or 0)
        return hours * 60 + minutes
    try:
        number = float(value)
        if number < 0:
            return None
        return number
    except ValueError:
        return None


def prompt_duration(label: str, examples: bool = False) -> float | None:
    example = " Examples: 45, 45m, 1h 20m, or 1:30." if examples else ""
    suffix = " Type 0 for none or not sure for unknown."
    while True:
        value = input(f"{label}{suffix}{example}: ").strip()
        if not value:
            print("Blank input is not supported. Type a duration, 0, or not sure.")
            continue
        if value.lower() in {"dk", "idk", "i don't know", "unknown", "not sure", "?"}:
            return None
        duration = parse_duration(value)
        if duration is not None:
            return duration
        print("Enter a time such as 45, 45m, 1h 20m, or 1:30. You can also type 0 or not sure.")


def prompt_choice(label: str, choices: list[str]) -> str:
    print(f"{label}:")
    for index, choice in enumerate(choices, start=1):
        print(f"  {index}. {choice}")
    while True:
        value = input("Choice number: ").strip()
        if value.isdigit() and 1 <= int(value) <= len(choices):
            return choices[int(value) - 1]
        print("Choose a listed number. Blank input is not supported.")


def prompt_bool(label: str) -> bool | str:
    while True:
        value = input(f"{label} (yes/no/not sure): ").strip().lower()
        if value in {"yes", "y"}:
            return True
        if value in {"no", "n"}:
            return False
        if value in {"not sure", "unsure", "idk", "i don't know", "??"}:
            return "not sure"
        print("Answer yes, no, or not sure. Blank input is not supported.")


def prompt_recorded_duration(label: str, recorded_minutes: float) -> float | None:
    while True:
        value = input(
            f"{label} Type `recorded` for {recorded_minutes:g}m, a duration, 0, or not sure: "
        ).strip()
        if not value:
            print("Blank input is not supported. Type recorded, a duration, 0, or not sure.")
            continue
        if value.lower() in {"recorded", "same", "accept"}:
            return recorded_minutes
        duration = parse_duration(value)
        if duration is not None or value.lower() in {
            "dk", "idk", "i don't know", "unknown", "not sure", "?"
        }:
            return duration
        print("Enter recorded, a duration such as 45m, 0, or not sure.")


class QuestionProgress:
    def __init__(self, total_questions: int) -> None:
        self.total_questions = total_questions
        self.current_question = 0

    def label(self, label: str) -> str:
        self.current_question += 1
        print(f"\nNext: Question {self.current_question} of {self.total_questions}")
        return label

    def skip(self, count: int, reason: str) -> None:
        self.total_questions -= count
        remaining = max(0, self.total_questions - self.current_question)
        print(f"Skipped {count} question(s) because {reason}. {remaining} question(s) remaining.")


def cmd_init(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    config_path = root / "config.json"
    if config_path.exists() and not args.overwrite:
        raise SystemExit(f"Config already exists: {config_path}")
    work_types = [item.strip() for item in args.work_types.split(",") if item.strip()]
    config = {
        "schema_version": SCHEMA_VERSION,
        "pilot_id": args.pilot_id,
        "participant_code": args.participant_code,
        "tool_name": args.tool_name,
        "pilot_start_date": args.start_date,
        "pilot_end_date": args.end_date,
        "gap_cutoff_minutes": args.gap_cutoff_minutes,
        "work_types": work_types,
        "standard_hourly_rate": args.standard_hourly_rate,
        "retention_date": args.retention_date,
        "form_url": args.form_url,
        "record_holder_role": args.record_holder_role,
        "timezone": args.timezone,
    }
    write_json(config_path, config)
    for folder in ("thread-metadata", "selected-threads", "submissions"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "local-records.jsonl").touch()
    (root / "submission-log.jsonl").touch()
    print(f"Initialized Real ROI pilot at {root}")


def cmd_extract(args: argparse.Namespace) -> None:
    config_path = Path(args.config).expanduser()
    config = load_config(config_path)
    root = config_path.parent
    if args.week:
        start_date, end_date = week_dates(config, args.week)
    else:
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
    parser_args = argparse.Namespace(
        secret=args.secret,
        secret_file=args.secret_file,
        keychain_service=args.keychain_service,
        keychain_account=args.keychain_account,
    )
    secret = load_thread_secret(parser_args)
    sessions, intervals = collect_intervals(
        Path(args.sessions_dir).expanduser(),
        start_date.isoformat(),
        end_date.isoformat(),
        str(config["timezone"]),
        int(config["gap_cutoff_minutes"]),
        secret,
    )
    metadata = derive_thread_metadata(
        sessions,
        intervals,
        str(config["timezone"]),
        int(config["gap_cutoff_minutes"]),
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "week": args.week,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "thread_count": len({item["thread_ref"] for item in metadata}),
        "threads": metadata,
    }
    output = root / "thread-metadata" / f"week-{args.week or 'custom'}.json"
    write_json(output, result)
    print(f"Extracted {result['thread_count']} thread(s) to {output}")


def cmd_select(args: argparse.Namespace) -> None:
    config_path = Path(args.config).expanduser()
    config = load_config(config_path)
    root = config_path.parent
    metadata_path = root / "thread-metadata" / f"week-{args.week}.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    threads = metadata["threads"]
    excluded = set(config.get("excluded_thread_refs", []))
    threads = [thread for thread in threads if thread["thread_ref"] not in excluded]
    if not threads:
        raise SystemExit("No threads available for selection.")
    ordered = sorted(threads, key=lambda item: float(item["derived_minutes"]), reverse=True)
    longest = ordered[0]
    remaining = ordered[1:]
    sample_count = min(2, len(remaining))
    seed = f"{config['participant_code']}:{args.week}"
    others = random.Random(seed).sample(remaining, sample_count) if sample_count else []
    selected = [longest, *others]
    result = {
        "schema_version": SCHEMA_VERSION,
        "week": args.week,
        "participant_code": config["participant_code"],
        "threads": selected,
    }
    output = root / "selected-threads" / f"week-{args.week}.json"
    write_json(output, result)
    print(f"Selected {len(selected)} thread(s) to {output}")


def cmd_checkin(args: argparse.Namespace) -> None:
    config_path = Path(args.config).expanduser()
    config = load_config(config_path)
    root = config_path.parent
    metadata_path = root / "thread-metadata" / f"week-{args.week}.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    excluded_refs = set(config.get("excluded_thread_refs", []))
    threads = [thread for thread in metadata["threads"] if thread["thread_ref"] not in excluded_refs]
    if not threads:
        raise SystemExit("No eligible threads found for this week.")

    work_types = list(config["work_types"])
    work_labels = [WORK_TYPE_LABELS.get(work_type, work_type) for work_type in work_types]
    derived_minutes = sum(float(thread["derived_minutes"]) for thread in threads)
    turn_count = sum(int(thread["turn_count"]) for thread in threads)

    print(f"\nWeek {args.week}: {metadata['start_date']} to {metadata['end_date']}")
    print(
        f"The Harness records show about {derived_minutes:g} minutes across "
        f"{len(threads)} thread(s) and {turn_count} turn(s)."
    )
    progress = QuestionProgress(17)
    print(
        "This check-in has up to 17 questions and should take about 5-8 minutes. "
        "Type 0 for none, or type not sure for unknown. Blank answers are not supported."
    )

    work_index = work_labels.index(
        prompt_choice(progress.label("What kind of work made up most of this time?"), work_labels)
    ) + 1
    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "participant_code": config["participant_code"],
        "week_number": args.week,
        "record_type": "weekly_aggregate",
        "start_date": metadata["start_date"],
        "end_date": metadata["end_date"],
        "work_type": work_types[work_index - 1],
        "thread_count": len(threads),
        "turn_count": turn_count,
        "derived_minutes": derived_minutes,
    }

    record["confirmed_minutes"] = prompt_recorded_duration(
        progress.label("How long did you actually spend with the Harness this week?"),
        derived_minutes,
    )

    baseline_labels = [choice[0] for choice in BASELINE_CHOICES]
    baseline_label = prompt_choice(
        progress.label("Thinking about this work overall, without the Harness how would you have handled it?"),
        baseline_labels,
    )
    baseline_method = dict(BASELINE_CHOICES)[baseline_label]
    record["baseline_method"] = baseline_method
    if baseline_method in {"would_not_have_done", "unknown"}:
        record["baseline_minutes"] = None
        progress.skip(1, "there is no baseline time to estimate")
    else:
        record["baseline_minutes"] = prompt_duration(
            progress.label("About how long would that work have taken?"),
            examples=True,
        )

    record["checking_fixing_minutes"] = prompt_duration(
        progress.label("This week, how long did you spend checking or fixing Harness results somewhere else?"),
        examples=True,
    )
    wrong_output = prompt_bool(
        progress.label("Did any output cause a real problem you had to clean up later?")
    )
    record["wrong_output_mattered"] = None if wrong_output == "not sure" else wrong_output is True
    if wrong_output is True:
        record["cleanup_minutes"] = prompt_duration(
            progress.label("About how long did cleanup take?"),
            examples=True,
        )
    else:
        record["cleanup_minutes"] = 0
        reason = "cleanup time is unknown" if wrong_output == "not sure" else "no cleanup problem was reported"
        progress.skip(1, reason)
    confidence_label = prompt_choice(
        progress.label("How solid are these numbers?"),
        ["Solid", "Rough but useful", "A guess"],
    )
    record["confidence"] = {
        "Solid": "high",
        "Rough but useful": "medium",
        "A guess": "low",
    }[confidence_label]

    new_capacity = prompt_bool(
        progress.label("Did you get anything new done this week because of the Harness?")
    )
    new_capacity_description = ""
    new_capacity_used_saved_time = False
    new_capacity_hours: float | None = 0
    if new_capacity is True:
        new_capacity_description = prompt_text(
            progress.label("In one sentence, what was the new work?")
        )
        new_capacity_used_saved_time = prompt_bool(
            progress.label("Did that work use time the Harness saved you?")
        ) is True
        new_capacity_duration = prompt_duration(
            progress.label("About how long did that new work take?"),
            examples=True,
        )
        new_capacity_hours = None if new_capacity_duration is None else new_capacity_duration / 60
    else:
        progress.skip(3, "no new work was reported")

    learning_duration = prompt_duration(
        progress.label("How much time did you spend learning the Harness this week?"),
        examples=True,
    )
    coordination_duration = prompt_duration(
        progress.label("How much time did you spend in meetings or messages about the Harness this week?"),
        examples=True,
    )
    model_changed = prompt_bool(
        progress.label("Did the model underneath the Harness change this week?")
    )
    model_change_redo_duration: float | None = 0
    if model_changed is True:
        model_change_redo_duration = prompt_duration(
            progress.label("How long did you spend redoing or adjusting work because of that change?"),
            examples=True,
        )
    else:
        reason = "model-change redo time is unknown" if model_changed == "not sure" else "the model did not change"
        progress.skip(1, reason)

    record.update(
        {
            "new_capacity_description": new_capacity_description,
            "new_capacity_would_not_have_happened": None if new_capacity == "not sure" else new_capacity is True,
            "new_capacity_used_saved_time": new_capacity_used_saved_time,
            "new_capacity_hours": new_capacity_hours,
            "learning_hours": None if learning_duration is None else learning_duration / 60,
            "coordination_hours": None if coordination_duration is None else coordination_duration / 60,
            "model_changed": None if model_changed == "not sure" else model_changed is True,
        }
    )
    record["model_change_redo_hours"] = (
        None if model_change_redo_duration is None else model_change_redo_duration / 60
    )
    records = [record]

    print("\nHere's what I'll save. Nothing is saved until you confirm.")
    for record in records:
        if record.get("record_type") == "weekly_aggregate":
            print(f"- Work type: {WORK_TYPE_LABELS.get(str(record['work_type']), record['work_type'])}")
            confirmed_minutes = record["confirmed_minutes"]
            print(f"- Harness time: {'not sure' if confirmed_minutes is None else f'{float(confirmed_minutes):g} minutes'}")
            print(f"- Without Harness: {record['baseline_minutes'] if record['baseline_minutes'] is not None else 'not sure'}")
            checking_minutes = record["checking_fixing_minutes"]
            print(f"- Checking/fixing: {'not sure' if checking_minutes is None else f'{float(checking_minutes):g} minutes'}")
            cleanup_minutes = record["cleanup_minutes"]
            print(f"- Cleanup: {'not sure' if cleanup_minutes is None else f'{float(cleanup_minutes):g} minutes'}")
            print(f"- New work: {record['new_capacity_description'] or 'none reported'}")
            learning_hours = record["learning_hours"]
            print(f"- Learning: {'not sure' if learning_hours is None else f'{float(learning_hours):g} hours'}")
            coordination_hours = record["coordination_hours"]
            print(f"- Meetings/messages: {'not sure' if coordination_hours is None else f'{float(coordination_hours):g} hours'}")
            redo_hours = record["model_change_redo_hours"]
            print(f"- Model-change redo: {'not sure' if redo_hours is None else f'{float(redo_hours):g} hours'}")
            print(f"- Estimate quality: {record['confidence']}")
        else:
            print(f"- {record['date']}: {WORK_TYPE_LABELS.get(str(record['work_type']), record['work_type'])}")
            print(f"  Harness time: {float(record['confirmed_minutes']):g} minutes")
            print(f"  Without Harness: {record['baseline_minutes'] if record['baseline_minutes'] is not None else 'not sure'}")
            print(f"  Checking/fixing: {float(record['checking_fixing_minutes']):g} minutes")
            print(f"  Cleanup: {float(record['cleanup_minutes']):g} minutes")
            print(f"  Estimate quality: {record['confidence']}")

    if prompt_bool(progress.label("Save these answers?")) is not True:
        print("Record not saved.")
        return
    confirmed_at = datetime.now().astimezone().isoformat()
    for record in records:
        record["participant_confirmed"] = True
        record["confirmed_at"] = confirmed_at
    output = root / "local-records.jsonl"
    for record in records:
        append_jsonl(output, record)
    print(f"Saved {len(records)} confirmed record(s) to {output}")


def cmd_submission(args: argparse.Namespace) -> None:
    config_path = Path(args.config).expanduser()
    config = load_config(config_path)
    root = config_path.parent
    records = [
        record
        for record in read_jsonl(root / "local-records.jsonl")
        if record.get("week_number") == args.week and record.get("participant_confirmed") is True
    ]
    if not records:
        raise SystemExit(f"No confirmed records found for week {args.week}.")
    output = root / "submissions" / f"week-{args.week}.md"
    lines = [
        f"# Real ROI Week {args.week} Submission",
        "",
        f"Participant code: `{config['participant_code']}`",
        "",
        "Enter these confirmed values in the Google Form. Do not add your name or email.",
        "",
    ]
    for record in records:
        record_type = record.get("record_type", "thread")
        heading = "Weekly aggregate" if record_type == "weekly_aggregate" else str(record_type)
        lines.append(f"## {heading} {record.get('thread_ref', '')}".rstrip())
        lines.append("")
        for key, value in record.items():
            if key in PROHIBITED_FIELDS:
                continue
            lines.append(f"- `{key}`: `{value}`")
        lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Submission summary written to {output}")


def cmd_validate(args: argparse.Namespace) -> None:
    config_path = Path(args.config).expanduser()
    root = config_path.parent
    records = read_jsonl(root / "local-records.jsonl")
    errors: list[str] = []
    for index, record in enumerate(records, start=1):
        if record.get("participant_confirmed") is not True:
            errors.append(f"Record {index} is not confirmed.")
        for field in PROHIBITED_FIELDS:
            if field in record:
                errors.append(f"Record {index} contains prohibited field {field}.")
        if "participant_code" not in record or "week_number" not in record:
            errors.append(f"Record {index} is missing participant code or week number.")
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Validated {len(records)} record(s). No prohibited fields found.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Initialize a local Real ROI pilot store")
    init.add_argument("--root", required=True)
    init.add_argument("--pilot-id", required=True)
    init.add_argument("--participant-code", required=True)
    init.add_argument("--tool-name", default="TritonAI Harness")
    init.add_argument("--start-date", required=True)
    init.add_argument("--end-date", required=True)
    init.add_argument("--work-types", required=True)
    init.add_argument("--gap-cutoff-minutes", type=int, default=10)
    init.add_argument("--standard-hourly-rate", type=float)
    init.add_argument("--retention-date")
    init.add_argument("--form-url")
    init.add_argument("--record-holder-role", default="Test subject")
    init.add_argument("--timezone", default="America/Los_Angeles")
    init.add_argument("--overwrite", action="store_true")
    init.set_defaults(func=cmd_init)

    extract = subparsers.add_parser("extract", help="Extract metadata-only thread activity")
    extract.add_argument("--config", required=True)
    extract.add_argument("--week", type=int)
    extract.add_argument("--start-date")
    extract.add_argument("--end-date")
    extract.add_argument("--sessions-dir", default="~/.tritonai-harness/codex/sessions")
    extract.add_argument("--secret")
    extract.add_argument("--secret-file")
    extract.add_argument("--keychain-service", default="real-roi-thread-secret")
    extract.add_argument("--keychain-account", default="")
    extract.set_defaults(func=cmd_extract)

    select = subparsers.add_parser("select", help="Select threads for a weekly check-in")
    select.add_argument("--config", required=True)
    select.add_argument("--week", type=int, required=True)
    select.set_defaults(func=cmd_select)

    checkin = subparsers.add_parser("checkin", help="Run an interactive weekly check-in")
    checkin.add_argument("--config", required=True)
    checkin.add_argument("--week", type=int, required=True)
    checkin.set_defaults(func=cmd_checkin)

    submission = subparsers.add_parser("submission", help="Create a Google Form submission summary")
    submission.add_argument("--config", required=True)
    submission.add_argument("--week", type=int, required=True)
    submission.set_defaults(func=cmd_submission)

    validate = subparsers.add_parser("validate", help="Validate local records")
    validate.add_argument("--config", required=True)
    validate.set_defaults(func=cmd_validate)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "extract" and not args.keychain_account:
        args.keychain_account = __import__("os").environ.get("USER", "")
    args.func(args)


if __name__ == "__main__":
    main()
