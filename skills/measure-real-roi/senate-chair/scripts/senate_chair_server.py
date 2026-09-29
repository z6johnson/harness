#!/usr/bin/env python3
"""Local-only interactive Senate Chair board server."""

from __future__ import annotations

import json
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from senate_chair import (  # noqa: E402
    STATUSES,
    find_case,
    load_all_cases,
    load_config,
    write_case_file,
)


class BoardServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler], root: Path):
        super().__init__(address, handler)
        self.root = root


class BoardRequestHandler(BaseHTTPRequestHandler):
    server: BoardServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404, "File not found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("Request body is empty")
        raw = self.rfile.read(length)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def _case_payload(self, case: dict) -> dict:
        deadline = case["deadlines"][0] if case["deadlines"] else None
        return {
            "id": case["id"],
            "title": case["title"],
            "status": case.get("Status", "Received"),
            "topic": case.get("Topic", "Other"),
            "owner": case.get("Owner", "unassigned"),
            "next_action": case.get("Next action", "awaiting triage"),
            "next_deadline": deadline["date"] if deadline else None,
            "updated": case.get("Last update", ""),
            "review_flag": case.get("Review flag", ""),
            "confidential": case.get("Confidential", "no") == "yes",
            "pending_unit": case.get("Pending unit", ""),
            "pending_since": case.get("Pending since", ""),
        }

    def _bootstrap(self) -> dict:
        cases = load_all_cases(self.server.root)
        config = load_config(self.server.root)
        return {
            "cases": [self._case_payload(case) for case in cases],
            "statuses": STATUSES,
            "topics": config["topics"],
            "generated": date.today().isoformat(),
        }

    def _update_case(self, case_id: str, changes: dict) -> dict:
        case = find_case(self.server.root, case_id)
        allowed = {"title", "owner", "next_action", "status", "topic", "pending_unit", "clear_review"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported fields: {', '.join(sorted(unknown))}")

        changed: list[str] = []
        if "title" in changes:
            title = str(changes["title"]).strip()
            if not title:
                raise ValueError("Title cannot be empty")
            if case["title"] != title:
                case["title"] = title
                changed.append("title")

        if "topic" in changes:
            topic = str(changes["topic"]).strip()
            topics = load_config(self.server.root)["topics"]
            if topic not in topics:
                raise ValueError(f"Unsupported topic: {topic}")
            if case.get("Topic", "") != topic:
                case["Topic"] = topic
                changed.append("topic")

        if "owner" in changes:
            owner = str(changes["owner"]).strip() or "unassigned"
            if case.get("Owner", "unassigned") != owner:
                case["Owner"] = owner
                changed.append("owner")

        if "next_action" in changes:
            next_action = str(changes["next_action"]).strip() or "awaiting triage"
            if case.get("Next action", "awaiting triage") != next_action:
                case["Next action"] = next_action
                changed.append("next action")

        if "status" in changes:
            status = str(changes["status"]).strip()
            if status not in STATUSES:
                raise ValueError(f"Unsupported status: {status}")
            if case.get("Status", "") != status:
                if status == "Pending":
                    pending_unit = str(changes.get("pending_unit", case.get("Pending unit", ""))).strip()
                    if not pending_unit:
                        raise ValueError("Pending cases require a pending unit")
                    case["Pending unit"] = pending_unit
                    case["Pending since"] = date.today().isoformat()
                else:
                    case["Pending unit"] = ""
                    case["Pending since"] = ""
                case["Status"] = status
                changed.append("status")

        if changes.get("clear_review") is True and case.get("Review flag"):
            case["Review flag"] = ""
            changed.append("review flag")

        if not changed:
            return self._case_payload(case)

        today = date.today().isoformat()
        case["Last update"] = today
        case["log"].append(f"{today}: Updated via interactive board ({', '.join(changed)})")
        write_case_file(self.server.root, case)
        return self._case_payload(case)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        board_dir = self.server.root / "board"
        if path in ("/", "/index.html"):
            self._send_file(board_dir / "index.html", "text/html; charset=utf-8")
        elif path == "/dashboard.css":
            self._send_file(board_dir / "dashboard.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self._send_file(board_dir / "app.js", "application/javascript; charset=utf-8")
        elif path == "/api/bootstrap":
            self._send_json(200, self._bootstrap())
        else:
            self.send_error(404, "Not found")

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/cases/"):
            self._send_json(404, {"error": "Not found"})
            return
        case_id = path[len("/api/cases/") :]
        try:
            changes = self._read_json_body()
            case = self._update_case(case_id, changes)
            self._send_json(200, case)
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
        except FileNotFoundError as error:
            self._send_json(404, {"error": str(error)})


def serve(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    require_root = root / "config.md"
    if not require_root.is_file():
        raise RuntimeError(f"Data root is not initialized: {require_root} is missing")
    server = BoardServer((host, port), BoardRequestHandler, root)
    print(f"Serving Senate Chair board at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
