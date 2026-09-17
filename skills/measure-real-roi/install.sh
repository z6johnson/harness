#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE=false
RUN_SETUP=true
INSTALL_MODE="auto"
COMMANDS_ONLY=false

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Options:
  --update        Replace an existing skill installation and skip guided setup
  --no-setup      Install without running first-time guided setup
  --github        Force installation through the Harness skill-installer
  --local         Force installation from this local checkout
  --commands-only Install only the local check-in commands
  -h, --help      Show this help

By default, a GitHub clone is installed with the official Harness skill-installer.
A ZIP download or unpublished checkout falls back to a validated local copy.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --update)
      UPDATE=true
      RUN_SETUP=false
      shift
      ;;
    --no-setup)
      RUN_SETUP=false
      shift
      ;;
    --github)
      INSTALL_MODE="github"
      shift
      ;;
    --local)
      INSTALL_MODE="local"
      shift
      ;;
    --commands-only)
      COMMANDS_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -n "${CODEX_HOME:-}" ]]; then
  CODEX_DEST="${CODEX_HOME%/}"
elif [[ -d "$HOME/.tritonai-harness/codex" ]]; then
  CODEX_DEST="$HOME/.tritonai-harness/codex"
else
  CODEX_DEST="$HOME/.codex"
fi

SKILL_SOURCE="$REPO_ROOT/skills/measure-real-roi"
SKILL_DEST="$CODEX_DEST/skills/measure-real-roi"
SKILL_DEST_PARENT="$CODEX_DEST/skills"
BIN_DIR="${REAL_ROI_BIN_DIR:-$HOME/.local/bin}"
SKILL_CREATOR_VALIDATOR="${REAL_ROI_SKILL_VALIDATOR:-$CODEX_DEST/skills/.system/skill-creator/scripts/quick_validate.py}"
SKILL_INSTALLER="${REAL_ROI_SKILL_INSTALLER:-$CODEX_DEST/skills/.system/skill-installer/scripts/install-skill-from-github.py}"

if [[ ! -d "$SKILL_SOURCE" ]]; then
  echo "Missing skill package: $SKILL_SOURCE" >&2
  exit 1
fi

if [[ ! -f "$SKILL_CREATOR_VALIDATOR" ]]; then
  echo "Harness skill-creator validator not found: $SKILL_CREATOR_VALIDATOR" >&2
  echo "Start TritonAI Harness or set REAL_ROI_SKILL_VALIDATOR." >&2
  exit 1
fi

echo "Validating skill with skill-creator..."
python3 "$SKILL_CREATOR_VALIDATOR" "$SKILL_SOURCE"

github_repo() {
  local remote_url
  remote_url="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
  [[ -z "$remote_url" ]] && return 1
  case "$remote_url" in
    git@github.com:*) remote_url="${remote_url#git@github.com:}" ;;
    https://github.com/*) remote_url="${remote_url#https://github.com/}" ;;
    http://github.com/*) remote_url="${remote_url#http://github.com/}" ;;
    *) return 1 ;;
  esac
  remote_url="${remote_url%.git}"
  [[ "$remote_url" == */* ]] || return 1
  printf '%s\n' "$remote_url"
}

install_from_github() {
  local repo ref temp_root
  repo="$(github_repo)" || {
    echo "No GitHub origin remote was found." >&2
    exit 1
  }
  ref="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || true)"
  [[ -n "$ref" ]] || ref="main"
  if [[ ! -f "$SKILL_INSTALLER" ]]; then
    echo "Harness skill-installer not found: $SKILL_INSTALLER" >&2
    echo "Start TritonAI Harness or set REAL_ROI_SKILL_INSTALLER." >&2
    exit 1
  fi

  temp_root="$(mktemp -d)"
  trap 'rm -rf "$temp_root"' RETURN
  echo "Installing skill with the official skill-installer..."
  python3 "$SKILL_INSTALLER" \
    --repo "$repo" \
    --path skills/measure-real-roi \
    --ref "$ref" \
    --dest "$temp_root/skills"
  python3 "$SKILL_CREATOR_VALIDATOR" "$temp_root/skills/measure-real-roi"
  rm -rf "$SKILL_DEST"
  mkdir -p "$SKILL_DEST_PARENT"
  mv "$temp_root/skills/measure-real-roi" "$SKILL_DEST"
}

install_locally() {
  echo "Installing skill from the local package..."
  rm -rf "$SKILL_DEST"
  mkdir -p "$SKILL_DEST"
  cp -R "$SKILL_SOURCE/." "$SKILL_DEST/"
  python3 "$SKILL_CREATOR_VALIDATOR" "$SKILL_DEST"
}

if [[ "$COMMANDS_ONLY" != true ]]; then
  if [[ -d "$SKILL_DEST" && "$UPDATE" != true ]]; then
    echo "Real ROI skill is already installed at $SKILL_DEST" >&2
    echo "Run ./install.sh --update to replace it, or ./install.sh --commands-only." >&2
    exit 1
  fi

  if [[ "$INSTALL_MODE" == "github" ]]; then
    install_from_github
  elif [[ "$INSTALL_MODE" == "local" ]]; then
    install_locally
  elif github_repo >/dev/null && [[ -f "$SKILL_INSTALLER" ]]; then
    install_from_github
  else
    install_locally
  fi
elif [[ ! -d "$SKILL_DEST" ]]; then
  echo "The skill is not installed at $SKILL_DEST" >&2
  echo "Run ./install.sh without --commands-only first." >&2
  exit 1
fi

chmod +x "$SKILL_DEST/scripts/real_roi.py" \
  "$SKILL_DEST/scripts/extract_thread_metadata.py" \
  "$SKILL_DEST/scripts/setup_real_roi.py" \
  "$SKILL_DEST/scripts/enable_real_roi.py"

if [[ -d "$HOME/.tritonai-harness" ]]; then
  DEFAULT_CONFIG="$HOME/.tritonai-harness/real-roi/harness-real-roi-pilot/config.json"
else
  DEFAULT_CONFIG="$HOME/.real-roi/harness-real-roi-pilot/config.json"
fi

python3 "$SKILL_DEST/scripts/enable_real_roi.py" \
  --bin-dir "$BIN_DIR" \
  --config "$DEFAULT_CONFIG" \
  --commands-only

echo
echo "Installed Real ROI skill to $SKILL_DEST"

if [[ "$RUN_SETUP" == true ]]; then
  echo
  "$BIN_DIR/real-roi-setup"
else
  echo "Guided setup skipped."
  if [[ ! -f "$DEFAULT_CONFIG" ]]; then
    echo "When ready, run: real-roi-setup"
  fi
fi

echo
echo "The skill will be available in new Harness or Codex conversations."
