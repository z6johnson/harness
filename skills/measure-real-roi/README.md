# Real ROI Skill

This repository packages the **Measure Real ROI** skill for local deployment in TritonAI Harness or Codex. It collects metadata-only AI-tool usage, asks one short weekly check-in, and prepares a pseudonymous submission for a restricted Google Form.

The skill measures the tool, not the person. It does not read or submit message content, attachments, file paths, raw session IDs, or thread titles.

## Install

Clone this repository, then run the installer:

```bash
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
./install.sh
```

If you prefer not to use Git, choose **Code → Download ZIP** on GitHub, unzip the file, open the folder in Terminal, and run `./install.sh`.

The installer:

1. validates the packaged skill with the Harness `skill-creator` validator
2. installs the skill with the official Harness `skill-installer` when the repository has a GitHub origin
3. falls back to a validated local copy for a ZIP download or unpublished checkout
4. installs `checkin`, `roi-checkin`, `real-roi-setup`, and `roi-setup` under `~/.local/bin`
5. adds that command directory to the shell path if needed
6. runs a plain-language guided setup for the participant code, pilot dates, work types, and local secret

When setup finishes, run:

```bash
checkin
```

To check in for another week:

```bash
roi-checkin 2
```

The skill becomes available in new Harness or Codex conversations. Existing conversations may need to be restarted.

## Requirements

- Python 3.9 or newer
- TritonAI Harness session logs, or a Codex session directory supplied through `REAL_ROI_SESSIONS_DIR`
- macOS uses Keychain; Linux and other platforms use a user-only local secret file

## Update or uninstall

Update an existing installation without changing local pilot data:

```bash
./install.sh --update
```

Force a local-copy installation when testing an unpublished checkout:

```bash
./install.sh --local
```

Force installation through the official Harness skill-installer:

```bash
./install.sh --github
```

If you prefer to run the official skill-installer directly:

```bash
python3 "${CODEX_HOME:-~/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo OWNER/REPOSITORY \
  --path skills/measure-real-roi
./install.sh --commands-only
```

Install the skill and commands now, but run guided setup later:

```bash
./install.sh --no-setup
real-roi-setup
```

Remove the skill and commands while keeping local records:

```bash
./uninstall.sh
```

Remove the skill, commands, and this pilot's local records:

```bash
./uninstall.sh --remove-data
```

## First-time checklist

- Assign a participant code that does not contain a name or email address.
- Review `skills/measure-real-roi/assets/consent-template.md` with each participant.
- Store the participant-code identity map separately from the analytical records.
- Confirm the retention date and restricted Google Form destination.
- Do not use the records for performance review or workload decisions.
- Run `checkin` once each week and confirm the summary before anything is saved.

## What stays local

The submitted weekly aggregate contains only the participant code, week, work type, time estimates, baseline estimate, checking/cleanup/learning/coordination/redo time, new-capacity answer, confidence, and thread/turn counts. It does not contain a submitted thread reference.

Thread references and metadata remain in the local pilot folder. On macOS, the pseudonymous thread secret is stored in Keychain. On other platforms, it is stored in a user-only `.thread-secret` file.

## Publish to GitHub

From the repository root:

```bash
git init
git add .
git commit -m "Add Real ROI skill package"
gh repo create OWNER/REPOSITORY --private --source . --push
```

Keep the repository private unless the pilot sponsor explicitly approves public distribution.
