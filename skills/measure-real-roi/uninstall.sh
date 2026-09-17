#!/usr/bin/env bash
set -euo pipefail

REMOVE_DATA=false
if [[ "${1:-}" == "--remove-data" ]]; then
  REMOVE_DATA=true
elif [[ -n "${1:-}" ]]; then
  echo "Usage: ./uninstall.sh [--remove-data]" >&2
  exit 1
fi

if [[ -n "${CODEX_HOME:-}" ]]; then
  CODEX_DEST="${CODEX_HOME%/}"
elif [[ -d "$HOME/.tritonai-harness/codex" ]]; then
  CODEX_DEST="$HOME/.tritonai-harness/codex"
else
  CODEX_DEST="$HOME/.codex"
fi

BIN_DIR="${REAL_ROI_BIN_DIR:-$HOME/.local/bin}"
rm -rf "$CODEX_DEST/skills/measure-real-roi"
rm -f "$BIN_DIR/roi-checkin" "$BIN_DIR/checkin" "$BIN_DIR/real-roi-setup" "$BIN_DIR/roi-setup"

if [[ "$REMOVE_DATA" == true ]]; then
  rm -rf "$HOME/.tritonai-harness/real-roi/harness-real-roi-pilot"
  rm -rf "$HOME/.real-roi/harness-real-roi-pilot"
  echo "Removed the skill, commands, and local pilot data."
else
  echo "Removed the skill and commands. Local pilot data was kept."
fi

