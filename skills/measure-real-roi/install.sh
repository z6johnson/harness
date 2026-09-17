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
  "$SKILL_DEST/scripts/setup_real_roi.py"
mkdir -p "$BIN_DIR"

if [[ -d "$HOME/.tritonai-harness" ]]; then
  DEFAULT_CONFIG="$HOME/.tritonai-harness/real-roi/harness-real-roi-pilot/config.json"
else
  DEFAULT_CONFIG="$HOME/.real-roi/harness-real-roi-pilot/config.json"
fi

cat > "$BIN_DIR/roi-checkin" <<WRAPPER
#!/usr/bin/env bash
set -euo pipefail

CONFIG="\${REAL_ROI_CONFIG:-$DEFAULT_CONFIG}"
SKILL="$SKILL_DEST/scripts/real_roi.py"
CODEX_HOME_DEFAULT="$CODEX_DEST"

if [[ ! -f "\$CONFIG" ]]; then
  echo "Real ROI is not configured yet." >&2
  echo "Run \`real-roi-setup\` first." >&2
  exit 1
fi

if [[ -n "\${1:-}" ]]; then
  WEEK="\$1"
else
  WEEK=\$(python3 - "\$CONFIG" <<'PY'
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

CONFIG_DIR="\$(dirname "\$CONFIG")"
if [[ -n "\${REAL_ROI_SESSIONS_DIR:-}" ]]; then
  SESSIONS_DIR="\$REAL_ROI_SESSIONS_DIR"
elif [[ -d "\$HOME/.tritonai-harness/codex/sessions" ]]; then
  SESSIONS_DIR="\$HOME/.tritonai-harness/codex/sessions"
else
  SESSIONS_DIR="\$CODEX_HOME_DEFAULT/sessions"
fi
if [[ "\$(uname)" == "Darwin" ]]; then
  SECRET_ARGS=(--keychain-service real-roi-thread-secret --keychain-account "\${USER:-\$(id -un)}")
else
  SECRET_ARGS=(--secret-file "\$CONFIG_DIR/.thread-secret")
fi

echo "Real ROI check-in: week \$WEEK"
python3 "\$SKILL" extract --config "\$CONFIG" --week "\$WEEK" --sessions-dir "\$SESSIONS_DIR" "\${SECRET_ARGS[@]}"
python3 "\$SKILL" checkin --config "\$CONFIG" --week "\$WEEK"
python3 "\$SKILL" submission --config "\$CONFIG" --week "\$WEEK"
WRAPPER

cat > "$BIN_DIR/real-roi-setup" <<WRAPPER
#!/usr/bin/env bash
set -euo pipefail

CONFIG="\${REAL_ROI_CONFIG:-$DEFAULT_CONFIG}"
exec python3 "$SKILL_DEST/scripts/setup_real_roi.py" --config "\$CONFIG" "\$@"
WRAPPER

chmod +x "$BIN_DIR/roi-checkin" "$BIN_DIR/real-roi-setup"
ln -sfn roi-checkin "$BIN_DIR/checkin"
ln -sfn real-roi-setup "$BIN_DIR/roi-setup"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo
    echo "$BIN_DIR is not currently in your PATH."
    read -r -p "Add it to your shell startup file now? [Y/n] " add_path || true
    add_path="${add_path:-Y}"
    if [[ "$add_path" =~ ^[Yy]$ ]]; then
      if [[ "$(uname)" == "Darwin" ]]; then
        SHELL_RC="$HOME/.zshrc"
      else
        SHELL_RC="$HOME/.profile"
      fi
      printf '\n# Real ROI local commands\nexport PATH="%s:$PATH"\n' "$BIN_DIR" >> "$SHELL_RC"
      echo "Added $BIN_DIR to $SHELL_RC."
      echo "Open a new terminal, or run: export PATH=\"$BIN_DIR:\$PATH\""
    else
      echo "To use the short commands, add this line to your shell startup file:"
      echo "export PATH=\"$BIN_DIR:\$PATH\""
    fi
    ;;
esac

echo
echo "Installed Real ROI skill to $SKILL_DEST"
echo "Installed commands to $BIN_DIR:"
echo "  - real-roi-setup (or roi-setup)"
echo "  - checkin (or roi-checkin)"

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
