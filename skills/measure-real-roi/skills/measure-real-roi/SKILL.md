---
name: measure-real-roi
description: Run local, pseudonymous Real ROI check-ins for AI tools. Use when the user asks to measure Real ROI, run a weekly AI ROI check-in, extract metadata-only Harness thread activity, prepare a pseudonymous Google Form submission, validate ROI records, or calculate institutional AI ROI.
---

# Measure Real ROI

Use this skill to collect local AI-tool usage data, confirm one aggregate weekly record with the participant, and prepare a pseudonymous submission. The skill measures the tool, not the person.

## Quick Start

0. For first-time deployment from the packaged repository, run `./install.sh`. It installs the skill, adds the local commands, and runs guided setup. To install without setup, use `./install.sh --no-setup`.
1. Read `references/governance.md` before setup or any question about consent, privacy, retention, or identity mapping.
2. Read `references/protocol.md` before running a weekly check-in.
3. Read `references/calculation.md` before computing or explaining ROI.
4. Use `scripts/real_roi.py` for local pilot setup, metadata extraction, aggregate check-in, submission, and validation.
5. Use `scripts/extract_thread_metadata.py` directly when only metadata extraction is needed.
6. Keep the check-in plain and short: state the question count and estimated time up front, show `Question X of Y` before every question, require an explicit answer, use `0` for none and `not sure` for unknown, and accept durations such as `45m`, `1h 20m`, or `1:30`.
7. After installation, the short command is `checkin` or `roi-checkin`. It runs extraction, one aggregate check-in, and the submission summary for the current week.

## Hard Rules

- Do not read, copy, summarize, or submit message content.
- Do not read attachment names, file paths, or raw session IDs into submitted records.
- Do not save or submit a record until the participant explicitly confirms it.
- Do not put names or email addresses in the analytical record.
- Keep the participant code and identity mapping separate.
- Treat "I don't know" as missing, not zero.
- Count each hour once.

## Local Commands

Initialize a pilot:

```bash
python3 scripts/real_roi.py init --root ~/.tritonai-harness/real-roi/<pilot-id> --pilot-id <pilot-id> --participant-code <code> --start-date YYYY-MM-DD --end-date YYYY-MM-DD --work-types "Data analysis,Writing,Code"
```

Extract metadata for a week:

```bash
python3 scripts/real_roi.py extract --config ~/.tritonai-harness/real-roi/<pilot-id>/config.json --week 1 --keychain-service real-roi-thread-secret --keychain-account "$USER"
```

Select sampled threads (legacy detailed mode only):

```bash
python3 scripts/real_roi.py select --config ~/.tritonai-harness/real-roi/<pilot-id>/config.json --week 1
```

Run the aggregate check-in:

```bash
checkin
```

Or run a specific week:

```bash
roi-checkin 2
```

Create a submission summary:

```bash
python3 scripts/real_roi.py submission --config ~/.tritonai-harness/real-roi/<pilot-id>/config.json --week 1
```

Validate local records:

```bash
python3 scripts/real_roi.py validate --config ~/.tritonai-harness/real-roi/<pilot-id>/config.json
```

## Resources

- `references/governance.md`: consent, privacy, access, retention, and identity mapping.
- `references/protocol.md`: setup, metadata extraction, aggregate coverage, weekly questions, and closing interviews.
- `references/calculation.md`: ROI terms, counting rules, formula, and reporting.
- `assets/consent-template.md`: participant agreement template.
- `assets/closing-interview.md`: closing interview guide.
- `assets/cost-intake.csv`: institutional cost intake template.
- `assets/capacity-valuation.csv`: new-capacity valuation template.
