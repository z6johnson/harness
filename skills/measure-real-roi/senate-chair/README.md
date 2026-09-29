# Senate Chair Skill

This folder packages the **Senate Chair** local operations skill for TritonAI Harness: guided setup, email/folder/pasted intake, case management, a local Kanban board, and a daily briefing.

## First run

After installing the skill, start a new Harness conversation and send:

```text
Use $senate-chair to initialize my data root and process new materials.
```

The skill asks for the Chair's email link (`Gmail`, `Outlook`, or intake-folder-only) and data-root location, then initializes the root, records the selected integration, generates the board, and continues into intake.

## Local actions

- **Process:** `Use $senate-chair to process my new materials.`
- **Board:** `Use $senate-chair to view my board.`
- **Briefing:** `Use $senate-chair to run my daily briefing.`
- **Status:** `Use $senate-chair to show my setup status.`

The exact command sequence is documented in `references/harness-actions.md`.

## Setup command

```bash
python3 scripts/senate_chair.py setup --root ~/SenateChair --account gmail
```

Use `--account outlook` for Outlook or `--account none` for intake-folder-only operation. The selected account is a label for the already-connected Harness integration; no credentials or OAuth tokens are stored.

The root is remembered in `~/.senate-chair/root`, so later `board`, `brief`, `list`, `mark`, `serve`, and `status` commands do not need `--root`.

## Distribution

Package this folder:

```bash
zip -r senate-chair.zip senate-chair/
```

Install it by unzipping it into `$CODEX_HOME/skills/senate-chair/`, or share the repository folder path through the Harness skill installer.
