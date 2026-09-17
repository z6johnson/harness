#!/usr/bin/env python3
"""Guided local setup for the Real ROI pilot."""

from __future__ import annotations

import argparse
import secrets
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path


DEFAULT_WORK_TYPES = "Data analysis,Writing,Code,Review,Planning"


def prompt_text(label: str, default: str | None = None, required: bool = False) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("This answer is required.")


def prompt_date(label: str, default: date) -> date:
    while True:
        value = prompt_text(label, default.isoformat())
        try:
            return date.fromisoformat(value)
        except ValueError:
            print("Enter the date as YYYY-MM-DD.")


def prompt_optional_float(label: str) -> float | None:
    while True:
        value = input(f"{label} [leave blank if not set yet]: ").strip()
        if not value:
            return None
        try:
            number = float(value)
            if number < 0:
                print("Enter a non-negative number.")
                continue
            return number
        except ValueError:
            print("Enter a number, or leave blank.")


def configure_secret(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        account = subprocess.run(["id", "-un"], check=True, capture_output=True, text=True).stdout.strip()
        check = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                "real-roi-thread-secret",
                "-w",
            ],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0 and check.stdout.strip():
            return
        print("Creating a local macOS Keychain secret for pseudonymous thread references...")
        secret = secrets.token_urlsafe(32)
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-a",
                account,
                "-s",
                "real-roi-thread-secret",
                "-w",
                secret,
            ],
            check=True,
        )
        return

    secret_path = root / ".thread-secret"
    if secret_path.exists():
        return
    print("Creating a local secret file for pseudonymous thread references...")
    secret = secrets.token_urlsafe(32)
    secret_path.write_text(secret + "\n", encoding="utf-8")
    secret_path.chmod(0o600)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config_path = Path(args.config).expanduser()
    root = config_path.parent

    if config_path.exists() and not args.overwrite:
        print(f"Real ROI is already configured at {config_path}")
        print("Run `checkin` to continue, or rerun setup with --overwrite to replace the pilot settings.")
        return

    print("Real ROI guided setup")
    print("The measurement records tool usage, not personal message content.")
    participant_code = prompt_text("Participant code", required=True)
    start_date = prompt_date("Pilot start date", date.today())
    end_date = prompt_date("Pilot end date", start_date + timedelta(days=41))
    retention_date = prompt_date("Record retention date", end_date + timedelta(days=80))
    work_types = prompt_text("Work types", DEFAULT_WORK_TYPES)
    timezone = prompt_text("Timezone", "America/Los_Angeles")
    standard_rate = prompt_optional_float("Standard hourly rate")
    form_url = prompt_text("Restricted Google Form URL")

    print("\nSetup summary")
    print(f"- Participant code: {participant_code}")
    print(f"- Pilot: {start_date.isoformat()} to {end_date.isoformat()}")
    print(f"- Retention date: {retention_date.isoformat()}")
    print(f"- Work types: {work_types}")
    print(f"- Local store: {root}")
    if form_url:
        print(f"- Form URL: {form_url}")
    else:
        print("- Form URL: not set yet")

    answer = prompt_text("Create this local pilot?", "yes").lower()
    if answer not in {"y", "yes"}:
        print("Setup canceled. Nothing was saved.")
        return

    configure_secret(root)
    skill_script = Path(__file__).with_name("real_roi.py")
    command = [
        sys.executable,
        str(skill_script),
        "init",
        "--root",
        str(root),
        "--pilot-id",
        "harness-real-roi-pilot",
        "--participant-code",
        participant_code,
        "--start-date",
        start_date.isoformat(),
        "--end-date",
        end_date.isoformat(),
        "--work-types",
        work_types,
        "--retention-date",
        retention_date.isoformat(),
        "--timezone",
        timezone,
    ]
    if standard_rate is not None:
        command.extend(["--standard-hourly-rate", str(standard_rate)])
    if form_url:
        command.extend(["--form-url", form_url])
    if args.overwrite:
        command.append("--overwrite")
    subprocess.run(command, check=True)

    print("\nSetup complete.")
    print("Run `checkin` when you are ready for your weekly check-in.")


if __name__ == "__main__":
    main()
