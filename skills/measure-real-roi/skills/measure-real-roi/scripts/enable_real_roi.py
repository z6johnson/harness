#!/usr/bin/env python3
"""Enable local Real ROI commands after the skill is installed."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path


def write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def default_config_path() -> Path:
    harness_root = Path.home() / ".tritonai-harness"
    root = harness_root / "real-roi" if harness_root.exists() else Path.home() / ".real-roi"
    return root / "harness-real-roi-pilot" / "config.json"


def add_to_path(bin_dir: Path) -> bool:
    path_value = os.environ.get("PATH", "")
    if str(bin_dir) in path_value.split(os.pathsep):
        return False
    shell_rc = Path.home() / (".zshrc" if sys.platform == "darwin" else ".profile")
    line = f'export PATH="{bin_dir}:$PATH"'
    existing = shell_rc.read_text(encoding="utf-8") if shell_rc.exists() else ""
    if line not in existing:
        with shell_rc.open("a", encoding="utf-8") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write("\n# Real ROI local commands\n")
            handle.write(line + "\n")
    return True


def install_commands(skill_root: Path, bin_dir: Path, config_path: Path) -> None:
    real_roi = skill_root / "scripts" / "real_roi.py"
    setup = skill_root / "scripts" / "setup_real_roi.py"

    checkin = f'''#!/usr/bin/env bash
set -euo pipefail

CONFIG="${{REAL_ROI_CONFIG:-{config_path}}}"
SKILL="{real_roi}"
CODEX_HOME_DEFAULT="${{CODEX_HOME:-$HOME/.codex}}"

if [[ ! -f "$CONFIG" ]]; then
  echo "Real ROI is not configured yet." >&2
  echo "Run real-roi-setup first." >&2
  exit 1
fi

if [[ -n "${{1:-}}" ]]; then
  WEEK="$1"
else
  WEEK=$(python3 - "$CONFIG" <<'PY'
import json
import sys
from datetime import date

with open(sys.argv[1], encoding="utf-8") as handle:
    config = json.load(handle)
start = date.fromisoformat(config["pilot_start_date"])
end = date.fromisoformat(config["pilot_end_date"])
today = date.today()
if today < start:
    print(1)
elif today > end:
    print(max(1, (end - start).days // 7 + 1))
else:
    print((today - start).days // 7 + 1)
PY
)
fi

CONFIG_DIR="$(dirname "$CONFIG")"
if [[ -n "${{REAL_ROI_SESSIONS_DIR:-}}" ]]; then
  SESSIONS_DIR="$REAL_ROI_SESSIONS_DIR"
elif [[ -d "$HOME/.tritonai-harness/codex/sessions" ]]; then
  SESSIONS_DIR="$HOME/.tritonai-harness/codex/sessions"
else
  SESSIONS_DIR="$CODEX_HOME_DEFAULT/sessions"
fi
if [[ "$(uname)" == "Darwin" ]]; then
  SECRET_ARGS=(--keychain-service real-roi-thread-secret --keychain-account "${{USER:-$(id -un)}}")
else
  SECRET_ARGS=(--secret-file "$CONFIG_DIR/.thread-secret")
fi

echo "Real ROI check-in: week $WEEK"
python3 "$SKILL" extract --config "$CONFIG" --week "$WEEK" --sessions-dir "$SESSIONS_DIR" "${{SECRET_ARGS[@]}}"
python3 "$SKILL" checkin --config "$CONFIG" --week "$WEEK"
python3 "$SKILL" submission --config "$CONFIG" --week "$WEEK"
'''

    setup_command = f'''#!/usr/bin/env bash
set -euo pipefail

CONFIG="${{REAL_ROI_CONFIG:-{config_path}}}"
exec python3 "{setup}" --config "$CONFIG" "$@"
'''

    write_executable(bin_dir / "roi-checkin", checkin)
    write_executable(bin_dir / "real-roi-setup", setup_command)
    for source, link_name in (("roi-checkin", "checkin"), ("real-roi-setup", "roi-setup")):
        link = bin_dir / link_name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(source)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local" / "bin")
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--commands-only", action="store_true")
    parser.add_argument("--no-add-path", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    skill_root = Path(__file__).resolve().parent.parent
    bin_dir = args.bin_dir.expanduser()
    config_path = args.config.expanduser()

    install_commands(skill_root, bin_dir, config_path)
    path_added = False if args.no_add_path else add_to_path(bin_dir)

    print(f"Enabled Real ROI commands in {bin_dir}:")
    print("  - real-roi-setup (or roi-setup)")
    print("  - checkin (or roi-checkin)")
    if path_added:
        print(f"Added {bin_dir} to your shell startup file.")
        print("Open a new terminal, or run:")
        print(f'  export PATH="{bin_dir}:$PATH"')

    if args.commands_only:
        return

    subprocess.run(
        [sys.executable, str(skill_root / "scripts" / "setup_real_roi.py"), "--config", str(config_path)],
        check=True,
    )


if __name__ == "__main__":
    main()
