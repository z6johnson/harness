# Measure Real ROI Skill

This repository packages the **Measure Real ROI** skill for TritonAI Harness. The skill sets up local commands, collects metadata-only AI-tool usage, runs one short weekly check-in, and prepares a pseudonymous submission for a restricted Google Form.

The skill measures the tool, not the person. It does not read or submit message content, attachments, file paths, raw session IDs, or thread titles.

## Distribution Options

### UCSD Community Skills

Use this path for UCSD participants who should not work with Git repositories.

1. Install the skill locally in TritonAI Harness.
2. Use the Harness **Share with UCSD** action for `measure-real-roi`.
3. After the community submission is approved, participants install it from the Harness community-skills interface.

**Share with UCSD submits the skill folder for public community review.** It does not submit local pilot data, participant codes, records, secrets, or Google Form responses.

### Skill Source URL

If the Harness installer asks for a **Skill source URL**, use the URL for the skill folder, not the repository root:

```text
https://github.com/OWNER/REPOSITORY/tree/main/skills/measure-real-roi
```

Replace `OWNER`, `REPOSITORY`, and `main` with the actual GitHub owner, repository, and branch.

If the installer separately asks for a repository and path, use:

```text
Repository: OWNER/REPOSITORY
Path: skills/measure-real-roi
```

## First Run For Participants

After installing the skill from Community Skills or a Skill source URL, participants should start a new Harness conversation and send:

```text
Use $measure-real-roi to enable Real ROI and set up my weekly check-in.
```

The skill runs `scripts/enable_real_roi.py`, which:

1. installs `checkin`, `roi-checkin`, `real-roi-setup`, and `roi-setup`
2. adds the command directory to the shell path when needed
3. starts guided setup for the participant code, pilot dates, work types, and local secret

If the participant is told to open a new terminal, they should do that and then run:

```bash
checkin
```

To check in for another week:

```bash
roi-checkin 2
```

The check-in announces its maximum question count and estimated time, then shows `Next: Question X of Y` before each question. It does not accept blank answers; type `0` for none, `not sure` for unknown, or `recorded` to accept the measured weekly total.

## Maintainer Installation

Maintainers can install directly from this checkout:

```bash
./install.sh --local
```

Update an existing installation without changing local pilot data:

```bash
./install.sh --update
```

Install the skill and commands now, but run guided setup later:

```bash
./install.sh --local --no-setup
real-roi-setup
```

Install only the local commands when the skill is already installed:

```bash
./install.sh --commands-only
```

Remove the skill and commands while keeping local records:

```bash
./uninstall.sh
```

Remove the skill, commands, and this pilot's local records:

```bash
./uninstall.sh --remove-data
```

## Requirements

- Python 3.9 or newer
- TritonAI Harness session logs, or a Codex session directory supplied through `REAL_ROI_SESSIONS_DIR`
- macOS stores the pseudonymous thread secret in Keychain; other platforms use a user-only `.thread-secret` file

## Governance Checklist

- Assign a participant code that does not contain a name or email address.
- Review `skills/measure-real-roi/assets/consent-template.md` with each participant.
- Store the participant-code identity map separately from analytical records.
- Confirm the retention date and restricted Google Form destination.
- Do not use records for performance review or workload decisions.
- Run `checkin` weekly and confirm the summary before anything is saved.

## What Stays Local

The submitted weekly aggregate contains only the participant code, week, work type, time estimates, baseline estimate, checking/cleanup/learning/coordination/redo time, new-capacity answer, confidence, and thread/turn counts. It does not contain a submitted thread reference.

Thread references and metadata remain in the local pilot folder. Local records, secrets, and submission summaries must not be committed to GitHub or shared through UCSD Community Skills.

## Publish To GitHub

Commit exactly:

```text
.gitignore
README.md
install.sh
uninstall.sh
skills/measure-real-roi/
```

From this repository root:

```bash
git add .
git commit -m "Add Measure Real ROI skill"
git branch -M main
gh repo create OWNER/REPOSITORY --private --source . --push
```

Keep the repository private unless the pilot sponsor explicitly approves public distribution.
