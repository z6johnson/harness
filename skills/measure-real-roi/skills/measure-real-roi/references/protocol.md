# Weekly Protocol

## Setup

1. Confirm pilot approval and consent.
2. Assign a participant code.
3. Confirm the work-type list.
4. Confirm the ten-minute gap cutoff.
5. Confirm the standard hourly rate.
6. Confirm P2 storage and retention.
7. Initialize the local store with `real_roi.py init`.
8. Configure the thread secret in the macOS Keychain.

## Metadata Extraction

Run `extract` for the pilot week. The parser:

- reads only session header and timestamp events
- skips response items that contain conversation content
- derives turn boundaries from `task_started` and `task_complete`
- merges activity separated by gaps no longer than the configured cutoff
- splits overlapping thread minutes
- emits only allowlisted metadata fields

The output contains a local thread reference, date, first and last activity, turn count, and derived minutes.
The aggregate check-in does not read or store thread titles.

## Aggregate Coverage

After extraction, the check-in uses every eligible thread in the week. It totals the derived minutes and turn count, then asks the participant one set of questions about overall usage. This avoids a long thread-by-thread interview and gives complete weekly coverage rather than a sample.

The `select` command remains available for a legacy detailed check-in, but the normal `checkin` command does not use it.

## Weekly Check-In

If the local `checkin` command is unavailable after a Community Skills or source-URL installation, run `scripts/enable_real_roi.py` first. It installs the local commands and starts guided setup.

Run `checkin` on this machine. The command automatically extracts the current week, runs the aggregate check-in, and creates the submission summary.

To run a different week, use `roi-checkin <week-number>`.

Run `checkin` and follow the prompts. The interface uses plain language and says up front that it has up to 17 questions and should take about 5-8 minutes. Every prompt shows `Next: Question X of Y`, and skipped follow-up questions reduce `Y` so the count stays accurate.

Blank input is not supported. Type `0` for none, `not sure` for unknown, or a duration such as `45`, `45m`, `1h 20m`, or `1:30`. To accept the recorded Harness total, type `recorded`.

The participant sees the week, total recorded minutes, thread count, and turn count, then answers once:

1. "What kind of work made up most of this time?" using friendly labels such as "Analysis or metrics" and "Writing or communication."
2. "How long did you actually spend with the Harness this week?" Type `recorded` to accept the recorded total.
3. "Thinking about this work overall, without the Harness how would you have handled it?" Choose the closest plain-language option.
4. "About how long would that work have taken?"
5. "This week, how long did you spend checking or fixing Harness results somewhere else?"
6. "Did any output cause a real problem you had to clean up later?"
7. If cleanup happened, "About how long did cleanup take?"
8. "How solid are these numbers?" Choose "Solid," "Rough but useful," or "A guess."

Then answer the remaining weekly questions:

1. "Did you get anything new done this week because of the Harness?"
2. If yes, describe it and say whether it used time the Harness saved.
3. "How much time did you spend learning the Harness this week?"
4. "How much time did you spend in meetings or messages about the Harness this week?"
5. "Did the model underneath the Harness change this week?"
6. If so, "How long did you spend redoing or adjusting work because of that change?"

Review the one-record summary. Save only if the participant confirms it. The saved record has `record_type: weekly_aggregate` and contains no submitted thread references.

## Submission

Run `submission` after confirmation. Enter the displayed values into the restricted Google Form. Do not add a name or email address.

## Closing Interview

Use `assets/closing-interview.md` at the end of the pilot. Start from the participant's records, correct mistakes, and discuss what the numbers left out.
