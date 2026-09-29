#!/usr/bin/env python3
"""Senate Chair local case management CLI.

Offline, standard library only. The AI layer produces structured payloads;
this tool validates them and maintains the case store, board, and briefing
data. It never makes a network request and never sends anything.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

STATUSES = ["Received", "Active", "Pending", "Resolved"]
PRIORITIES = ["Urgent", "High", "Normal", "Low"]
CONFIDENCE_LEVELS = ["high", "medium", "low"]
SOURCE_TYPES = ["email", "file", "pasted"]
BUILT_IN_TOPICS = [
    "Budget",
    "Faculty Affairs",
    "Academic Personnel",
    "Governance and Bylaws",
    "Curriculum",
    "Student Matters",
    "Research Administration",
    "Facilities and Space",
    "Communications and Media",
    "Government and External Relations",
    "Events and Ceremonies",
    "Awards and Recognition",
    "Other",
]
META_KEYS = [
    "Status",
    "Topic",
    "Owner",
    "Suggested owner",
    "Opened",
    "Last update",
    "Next action",
    "Review flag",
    "Pending unit",
    "Pending since",
    "Confidential",
]
CASE_HEADING_RE = re.compile(r"^(SC-\d{4}-\d{3}):\s*(.*)$")
ITEM_ENTRY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{3}):\s*(.*)$")
DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def emit(payload: dict | list) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def parse_iso_date(value, label: str = "date") -> date:
    text = str(value).strip()
    if not DATE_ONLY_RE.match(text):
        fail(f"Invalid {label}: {value!r} (expected YYYY-MM-DD)")
    try:
        return date.fromisoformat(text)
    except ValueError:
        fail(f"Invalid {label}: {value!r}")


def require_root(root: Path) -> None:
    config = root / "config.md"
    if not config.is_file():
        fail(f"Data root is not initialized: {config} is missing. Run the init command first.")


def load_config(root: Path) -> dict:
    text = (root / "config.md").read_text(encoding="utf-8")
    topics = list(BUILT_IN_TOPICS)
    last_mail_run = "none"
    last_briefing = "none"
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section == "Extra topics" and line.startswith("- "):
            topic = line[2:].strip()
            if topic and topic not in topics:
                topics.append(topic)
        elif line.startswith("- Last mail run:"):
            last_mail_run = line.split(":", 1)[1].strip()
        elif line.startswith("- Last briefing:"):
            last_briefing = line.split(":", 1)[1].strip()
    return {"topics": topics, "last_mail_run": last_mail_run, "last_briefing": last_briefing}


def update_config(root: Path, key: str, value: str) -> None:
    path = root / "config.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    needle = f"- {key}:"
    output = []
    found = False
    for line in lines:
        if line.startswith(needle):
            output.append(f"- {key}: {value}")
            found = True
        else:
            output.append(line)
    if not found:
        output.append("")
        output.append(f"- {key}: {value}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def unescape_cell(text: str) -> str:
    return text.replace("\\|", "|")


def parse_case_file(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    meta = {key: "" for key in META_KEYS}
    meta["Owner"] = "unassigned"
    deadlines: list[dict] = []
    log: list[str] = []
    items: list[str] = []
    case_id = ""
    title = ""
    section = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("# ") and not case_id:
            match = CASE_HEADING_RE.match(line[2:].strip())
            if match:
                case_id, title = match.group(1), match.group(2).strip()
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if line.startswith("- ") and section is None:
            body = line[2:]
            for key in META_KEYS:
                if body.startswith(f"{key}:"):
                    meta[key] = body[len(key) + 1 :].strip()
                    break
            continue
        if section == "Deadlines" and line.startswith("|"):
            cells = [unescape_cell(cell.strip()) for cell in line.strip().strip("|").split("|")]
            if len(cells) != 4:
                continue
            if cells[0] in ("Deadline", "") or set(cells[0]) <= {"-"}:
                continue
            deadlines.append(
                {"date": cells[0], "source": cells[1], "item": cells[2], "done": cells[3]}
            )
        elif section == "Log" and line.startswith("- "):
            log.append(line[2:].strip())
        elif section == "Items" and line.startswith("- "):
            items.append(line[2:].strip())
    if not case_id:
        return None
    case = {"id": case_id, "title": title, "path": str(path)}
    case.update(meta)
    case["deadlines"] = deadlines
    case["log"] = log
    case["items"] = items
    return case


def write_case_file(root: Path, case: dict) -> Path:
    case_dir = root / "cases" / case["id"]
    (case_dir / "items").mkdir(parents=True, exist_ok=True)
    path = case_dir / "case.md"
    lines = [f"# {case['id']}: {case['title']}", ""]
    for key in META_KEYS:
        value = case.get(key, "")
        if value != "":
            lines.append(f"- {key}: {value}")
    lines += ["", "## Deadlines"]
    if case["deadlines"]:
        lines.append("| Deadline | Source sentence | Item | Done |")
        lines.append("|---|---|---|---|")
        for entry in case["deadlines"]:
            lines.append(
                "| {date} | {source} | {item} | {done} |".format(
                    date=escape_cell(entry["date"]),
                    source=escape_cell(entry["source"]),
                    item=escape_cell(entry["item"]),
                    done=escape_cell(entry["done"]),
                )
            )
    else:
        lines.append("None yet.")
    lines += ["", "## Log"]
    if case["log"]:
        lines.extend(f"- {entry}" for entry in case["log"])
    else:
        lines.append("- None yet.")
    lines += ["", "## Items"]
    if case["items"]:
        lines.extend(f"- {entry}" for entry in case["items"])
    else:
        lines.append("- None yet.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_all_cases(root: Path) -> list[dict]:
    cases: list[dict] = []
    cases_dir = root / "cases"
    if not cases_dir.is_dir():
        return cases
    for child in sorted(cases_dir.iterdir()):
        case_path = child / "case.md"
        if case_path.is_file():
            case = parse_case_file(case_path)
            if case is not None:
                cases.append(case)
    return cases


def find_case(root: Path, case_id: str) -> dict:
    if not re.match(r"^SC-\d{4}-\d{3}$", case_id):
        fail(f"Invalid case ID: {case_id!r} (expected SC-YYYY-NNN)")
    path = root / "cases" / case_id / "case.md"
    if not path.is_file():
        fail(f"Case not found: {case_id}")
    case = parse_case_file(path)
    if case is None:
        fail(f"Case file is unreadable: {path}")
    return case


def next_case_id(root: Path, today: date) -> str:
    year = today.year
    max_seq = 0
    cases_dir = root / "cases"
    if cases_dir.is_dir():
        for child in cases_dir.iterdir():
            match = re.match(r"^SC-(\d{4})-(\d{3})$", child.name)
            if match and int(match.group(1)) == year:
                max_seq = max(max_seq, int(match.group(2)))
    return f"SC-{year}-{max_seq + 1:03d}"


def next_item_id(root: Path, received: date) -> str:
    day = received.isoformat()
    pattern = re.compile(re.escape(day) + r"-(\d{3})\.md$")
    max_seq = 0
    items_dir = root / "cases"
    if items_dir.is_dir():
        for path in items_dir.glob("*/items/*.md"):
            match = pattern.search(path.name)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
    return f"{day}-{max_seq + 1:03d}"


def headline_from_summary(summary: str) -> str:
    first_sentence = re.split(r"(?<=[.!?])\s+", summary.strip(), maxsplit=1)[0]
    if len(first_sentence) > 100:
        first_sentence = first_sentence[:97].rstrip() + "..."
    return first_sentence


def next_deadline(case: dict) -> dict | None:
    open_deadlines = [entry for entry in case["deadlines"] if entry["done"].lower() != "yes"]
    if not open_deadlines:
        return None
    return min(open_deadlines, key=lambda entry: entry["date"])


def cmd_init(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    config = root / "config.md"
    if config.exists():
        fail(f"{config} already exists; refusing to overwrite an initialized data root.")
    for folder in ("intake", "cases", "board", "briefings", "tmp"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    config.write_text(
        "\n".join(
            [
                "# Senate Chair Data Root",
                "",
                f"- Data root: {root}",
                "- Last mail run: none",
                "- Last briefing: none",
                "",
                "## Extra topics",
                "",
                "Add one topic per line, formatted as `- Topic`.",
                "",
                "## Owners and units",
                "",
                "Add one owner or unit per line, formatted as `- Name`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    emit({"root": str(root), "initialized": True})


def read_payload(path: str) -> dict:
    payload_path = Path(path).expanduser()
    if not payload_path.is_file():
        fail(f"Payload file not found: {payload_path}")
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Payload is not valid JSON: {exc}")
    if not isinstance(payload, dict):
        fail("Payload must be a JSON object.")
    return payload


def cmd_process(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    require_root(root)
    config = load_config(root)
    payload = read_payload(args.payload)

    for key in ("source", "received", "summary", "topic", "priority", "deadlines", "case"):
        if key not in payload:
            fail(f"Payload missing required key: {key}")

    source = payload["source"]
    if not isinstance(source, dict) or source.get("type") not in SOURCE_TYPES:
        fail("source.type must be one of: email, file, pasted")
    source_ref = str(source.get("ref", "")).strip()
    if source["type"] != "pasted" and not source_ref:
        fail("source.ref is required for email and file items")
    if source["type"] == "pasted":
        source_display = "pasted"
    else:
        source_display = f"{source['type']} <{source_ref}>"

    received = parse_iso_date(payload["received"], "received date")
    summary = str(payload["summary"]).strip()
    if not summary:
        fail("summary must not be empty")
    word_count = len(summary.split())
    if word_count > 120:
        fail(f"summary is {word_count} words; the limit is 120")

    topic = str(payload["topic"]).strip()
    if topic not in config["topics"]:
        fail(f"Unknown topic: {topic!r}. Use a label from taxonomy.md or config.md Extra topics.")

    priority = str(payload["priority"]).strip()
    if priority not in PRIORITIES:
        fail(f"Invalid priority: {priority!r} (expected one of {', '.join(PRIORITIES)})")

    raw_deadlines = payload["deadlines"]
    if not isinstance(raw_deadlines, list):
        fail("deadlines must be a list")
    deadlines = []
    for entry in raw_deadlines:
        if not isinstance(entry, dict) or "date" not in entry or "source" not in entry:
            fail("Each deadline needs a date and a source sentence.")
        deadline_date = parse_iso_date(entry["date"], "deadline date")
        deadline_source = str(entry["source"]).strip()
        if not deadline_source:
            fail("A deadline source sentence must not be empty.")
        deadlines.append({"date": deadline_date.isoformat(), "source": deadline_source})

    case_spec = payload["case"]
    if not isinstance(case_spec, dict):
        fail("case must be a JSON object")
    confidence = str(case_spec.get("confidence", "")).strip()
    if confidence not in CONFIDENCE_LEVELS:
        fail("case.confidence must be high, medium, or low")
    reason = str(case_spec.get("reason", "")).strip()
    if not reason:
        fail("case.reason is required")
    suggested_owner = str(case_spec.get("suggested_owner", "")).strip()
    suggested_next = str(case_spec.get("suggested_next_action", "")).strip()
    confidential = bool(payload.get("confidential", False))

    today = date.today()
    item_id = next_item_id(root, received)
    action = case_spec.get("action")
    if action == "new":
        title = str(case_spec.get("title", "")).strip()
        if not title:
            fail("case.title is required for a new case")
        if len(title) > 120:
            fail("case.title must be 120 characters or fewer")
        case_id = next_case_id(root, today)
        case = {key: "" for key in META_KEYS}
        case.update(
            {
                "id": case_id,
                "title": title,
                "Status": "Received",
                "Topic": topic,
                "Owner": "unassigned",
                "Suggested owner": suggested_owner,
                "Opened": today.isoformat(),
                "Last update": today.isoformat(),
                "Next action": "awaiting triage",
                "Review flag": "new case unreviewed",
                "Confidential": "yes" if confidential else "no",
                "deadlines": [],
                "log": [],
                "items": [],
            }
        )
        new_case = True
    elif action == "existing":
        case_id = str(case_spec.get("id", "")).strip()
        case = find_case(root, case_id)
        new_case = False
    else:
        fail("case.action must be 'new' or 'existing'")

    for deadline in deadlines:
        duplicate = any(
            entry["date"] == deadline["date"] and entry["source"] == deadline["source"]
            for entry in case["deadlines"]
        )
        if not duplicate:
            case["deadlines"].append({**deadline, "item": item_id, "done": "no"})

    case["Last update"] = today.isoformat()
    if confidential:
        case["Confidential"] = "yes"
    if not new_case and confidence in ("medium", "low") and not case["Review flag"]:
        case["Review flag"] = f"auto-link {confidence} confidence"

    action_word = "Opened with" if new_case else "Added"
    case["log"].append(f"{today.isoformat()}: {action_word} item {item_id} ({confidence} confidence).")
    case["items"].append(f"{item_id}: {headline_from_summary(summary)}")

    item_path = root / "cases" / case["id"] / "items" / f"{item_id}.md"
    item_path.parent.mkdir(parents=True, exist_ok=True)
    item_lines = [
        f"# Item {item_id}",
        f"- Source: {source_display}",
        f"- Received: {received.isoformat()}",
        f"- Case: {case['id']}",
        f"- Topic: {topic}",
        f"- Priority: {priority}",
        f"- Link confidence: {confidence} — {reason}",
        "",
        "## Summary",
        summary,
        "",
        "## Deadlines",
    ]
    if deadlines:
        item_lines.extend(f"- {entry['date']}: {entry['source']}" for entry in deadlines)
    else:
        item_lines.append("None.")
    item_path.write_text("\n".join(item_lines) + "\n", encoding="utf-8")
    write_case_file(root, case)
    board_path = generate_board(root)
    emit(
        {
            "case_id": case["id"],
            "item_id": item_id,
            "item_path": str(item_path),
            "new_case": new_case,
            "status": case["Status"],
            "review_flag": case["Review flag"],
            "board_path": str(board_path),
        }
    )


def cmd_triage(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    require_root(root)
    case = find_case(root, args.case)
    today = date.today().isoformat()

    has_change = any(
        (
            args.status,
            args.owner is not None,
            args.next_action is not None,
            args.clear_review,
        )
    )
    if not has_change:
        fail("Nothing to update; provide --status, --owner, --next-action, or --clear-review.")
    if args.pending_unit and args.status != "Pending":
        fail("--pending-unit is only valid together with --status Pending.")

    changes: list[str] = []
    if args.status:
        if args.status not in STATUSES:
            fail(f"Invalid status: {args.status!r} (expected one of {', '.join(STATUSES)})")
        case["Status"] = args.status
        changes.append(f"status -> {args.status}")
        if args.status == "Pending":
            if args.pending_unit:
                case["Pending unit"] = args.pending_unit
                case["Pending since"] = today
            elif not case.get("Pending unit"):
                fail("Pending requires --pending-unit.")
        else:
            case["Pending unit"] = ""
            case["Pending since"] = ""
    if args.owner is not None:
        case["Owner"] = args.owner.strip() or "unassigned"
        changes.append(f"owner -> {case['Owner']}")
    if args.next_action is not None:
        case["Next action"] = args.next_action.strip()
        changes.append(f"next action -> {case['Next action']}")
    if args.clear_review:
        case["Review flag"] = ""
        changes.append("review flag cleared")

    case["Last update"] = today
    case["log"].append(f"{today}: Triage — {'; '.join(changes)}.")
    write_case_file(root, case)
    board_path = generate_board(root)
    emit(
        {
            "case_id": case["id"],
            "status": case["Status"],
            "owner": case["Owner"],
            "next_action": case["Next action"],
            "review_flag": case["Review flag"],
            "board_path": str(board_path),
        }
    )


def deadline_label(deadline: dict, today: date) -> tuple[str, str]:
    deadline_date = date.fromisoformat(deadline["date"])
    days = (deadline_date - today).days
    if days < 0:
        label = f"{deadline['date']} (overdue {-days}d)"
    elif days == 0:
        label = f"{deadline['date']} (today)"
    else:
        label = f"{deadline['date']} (in {days}d)"
    css = "dl-red" if days <= 3 else "dl-amber" if days <= 7 else "dl-normal"
    return label, css


def render_card(case: dict, today: date) -> str:
    deadline = next_deadline(case)
    if deadline:
        deadline_text, deadline_css = deadline_label(deadline, today)
    else:
        deadline_text, deadline_css = "None", "dl-normal"
    last_update = case.get("Last update", "")
    if last_update:
        update_days = (today - date.fromisoformat(last_update)).days
        updated_text = "today" if update_days <= 0 else f"{update_days}d ago"
    else:
        updated_text = "unknown"

    badges = []
    if case.get("Review flag"):
        badges.append(f'<span class="badge review">Review: {html.escape(case["Review flag"])}</span>')
    if case.get("Confidential") == "yes":
        badges.append('<span class="badge confidential">Confidential</span>')
    pending_rows = ""
    if case["Status"] == "Pending" and case.get("Pending unit"):
        since = case.get("Pending since", "")
        if since:
            waiting = (today - date.fromisoformat(since)).days
            waiting_text = f"{waiting}d" if waiting >= 0 else "unknown"
        else:
            waiting_text = "unknown"
        badges.append(
            f'<span class="badge pending">Waiting on {html.escape(case["Pending unit"])} · {waiting_text}</span>'
        )

    return (
        '<article class="card">'
        '<div class="card-top">'
        f'<span class="cid">{html.escape(case["id"])}</span>'
        f'<span class="chip">{html.escape(case.get("Topic", "Other"))}</span>'
        "</div>"
        f"<h3>{html.escape(case['title'])}</h3>"
        "<dl>"
        f'<div><dt>Owner</dt><dd>{html.escape(case.get("Owner", "unassigned"))}</dd></div>'
        f'<div><dt>Next deadline</dt><dd class="{deadline_css}">{html.escape(deadline_text)}</dd></div>'
        f'<div><dt>Updated</dt><dd>{html.escape(updated_text)}</dd></div>'
        "</dl>"
        + (f'<div class="badges">{"".join(badges)}</div>' if badges else "")
        + "</article>"
    )


def generate_board(root: Path) -> Path:
    cases = load_all_cases(root)
    today = date.today()
    columns = {status: [] for status in STATUSES}
    for case in cases:
        status = case.get("Status", "")
        if status not in columns:
            fail(f"Case {case['id']} has an invalid status: {status!r}")
        columns[status].append(case)

    template_path = Path(__file__).resolve().parent.parent / "assets" / "dashboard-template.html"
    if not template_path.is_file():
        fail(f"Dashboard template missing: {template_path}")
    board_html = template_path.read_text(encoding="utf-8")
    board_html = board_html.replace("{{GENERATED}}", today.isoformat())

    for status in STATUSES:
        column_cases = sorted(
            columns[status],
            key=lambda case: (
                (next_deadline(case) or {"date": "9999-12-31"})["date"],
                case.get("Last update") or "9999-12-31",
            ),
        )
        if column_cases:
            cards = "".join(render_card(case, today) for case in column_cases)
        else:
            cards = '<p class="empty">Nothing here.</p>'
        board_html = board_html.replace(f"<!-- CARDS:{status.upper()} -->", cards)
        board_html = board_html.replace(f"{{{{COUNT_{status.upper()}}}}}", str(len(column_cases)))

    board_dir = root / "board"
    board_dir.mkdir(parents=True, exist_ok=True)
    board_path = board_dir / "index.html"
    board_path.write_text(board_html, encoding="utf-8")
    return board_path


def cmd_board(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    require_root(root)
    board_path = generate_board(root)
    cases = load_all_cases(root)
    counts = {status: 0 for status in STATUSES}
    for case in cases:
        if case.get("Status") in counts:
            counts[case["Status"]] += 1
    emit({"board_path": str(board_path), "counts": counts})


def cmd_brief(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    require_root(root)
    config = load_config(root)
    today = parse_iso_date(args.date, "briefing date") if args.date else date.today()
    horizon = today + timedelta(days=7)

    deadlines = []
    pending = []
    stalled = []
    new_items = []

    cutoff = today
    if config["last_briefing"] not in ("", "none"):
        cutoff = parse_iso_date(config["last_briefing"], "last briefing date")

    for case in load_all_cases(root):
        for entry in case["deadlines"]:
            if entry["done"].lower() == "yes":
                continue
            entry_date = date.fromisoformat(entry["date"])
            if entry_date <= horizon:
                deadlines.append(
                    {
                        "case_id": case["id"],
                        "title": case["title"],
                        "date": entry["date"],
                        "days": (entry_date - today).days,
                        "source": entry["source"],
                    }
                )
        if case.get("Status") == "Pending":
            since = case.get("Pending since", "")
            days_waiting = (today - date.fromisoformat(since)).days if since else None
            pending.append(
                {
                    "case_id": case["id"],
                    "title": case["title"],
                    "unit": case.get("Pending unit", ""),
                    "days_waiting": days_waiting,
                }
            )
        if case.get("Status") == "Active" and case.get("Last update"):
            days_idle = (today - date.fromisoformat(case["Last update"])).days
            if days_idle >= 5:
                stalled.append(
                    {
                        "case_id": case["id"],
                        "title": case["title"],
                        "owner": case.get("Owner", "unassigned"),
                        "days_since_update": days_idle,
                    }
                )
        for entry in case["items"]:
            match = ITEM_ENTRY_RE.match(entry)
            if not match:
                continue
            received = date.fromisoformat(match.group(1))
            if cutoff < received <= today:
                new_items.append(
                    {
                        "case_id": case["id"],
                        "item_id": f"{match.group(1)}-{match.group(2)}",
                        "summary": match.group(3),
                    }
                )

    deadlines.sort(key=lambda entry: (entry["date"], entry["case_id"]))
    pending.sort(key=lambda entry: (-(entry["days_waiting"] or -1), entry["case_id"]))
    stalled.sort(key=lambda entry: (-entry["days_since_update"], entry["case_id"]))
    update_config(root, "Last briefing", today.isoformat())
    emit(
        {
            "briefing_date": today.isoformat(),
            "deadlines": deadlines,
            "pending": pending,
            "stalled": stalled,
            "new_items": new_items,
        }
    )


def cmd_list(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    require_root(root)
    cases = load_all_cases(root)
    if args.status:
        if args.status not in STATUSES:
            fail(f"Invalid status filter: {args.status!r}")
        cases = [case for case in cases if case.get("Status") == args.status]
    if args.topic:
        cases = [case for case in cases if case.get("Topic", "") == args.topic]
    rows = []
    for case in sorted(cases, key=lambda case: case["id"]):
        deadline = next_deadline(case)
        rows.append(
            {
                "id": case["id"],
                "title": case["title"],
                "status": case.get("Status", ""),
                "topic": case.get("Topic", ""),
                "owner": case.get("Owner", "unassigned"),
                "next_deadline": deadline["date"] if deadline else None,
                "review_flag": case.get("Review flag", ""),
            }
        )
    emit(rows)


def cmd_mark(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser()
    require_root(root)
    if not args.mail_run:
        fail("Provide --mail-run YYYY-MM-DD.")
    mail_run = parse_iso_date(args.mail_run, "mail run date")
    update_config(root, "Last mail run", mail_run.isoformat())
    emit({"last_mail_run": mail_run.isoformat()})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create the data root")
    init_parser.add_argument("--root", default="~/SenateChair")
    init_parser.set_defaults(func=cmd_init)

    process_parser = subparsers.add_parser("process", help="persist one processed item")
    process_parser.add_argument("--root", required=True)
    process_parser.add_argument("--payload", required=True)
    process_parser.set_defaults(func=cmd_process)

    triage_parser = subparsers.add_parser("triage", help="apply Chair-confirmed case decisions")
    triage_parser.add_argument("--root", required=True)
    triage_parser.add_argument("--case", required=True)
    triage_parser.add_argument("--status", choices=STATUSES)
    triage_parser.add_argument("--owner")
    triage_parser.add_argument("--next-action")
    triage_parser.add_argument("--pending-unit")
    triage_parser.add_argument("--clear-review", action="store_true")
    triage_parser.set_defaults(func=cmd_triage)

    board_parser = subparsers.add_parser("board", help="regenerate the Kanban dashboard")
    board_parser.add_argument("--root", required=True)
    board_parser.set_defaults(func=cmd_board)

    brief_parser = subparsers.add_parser("brief", help="print the daily briefing data skeleton")
    brief_parser.add_argument("--root", required=True)
    brief_parser.add_argument("--date")
    brief_parser.set_defaults(func=cmd_brief)

    list_parser = subparsers.add_parser("list", help="list cases")
    list_parser.add_argument("--root", required=True)
    list_parser.add_argument("--status", choices=STATUSES)
    list_parser.add_argument("--topic")
    list_parser.set_defaults(func=cmd_list)

    mark_parser = subparsers.add_parser("mark", help="record the last processed mail date")
    mark_parser.add_argument("--root", required=True)
    mark_parser.add_argument("--mail-run")
    mark_parser.set_defaults(func=cmd_mark)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
