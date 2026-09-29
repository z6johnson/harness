# Senate Chair Workflow

## Intake

1. Mail: search the Chair's own mailbox for messages received after the last-mail-run timestamp in `config.md`. Update the timestamp with `mark --root <root> --mail-run YYYY-MM-DD` only after all new messages are processed.
2. Files: list unprocessed files in `<root>/intake/` and process each. Leave originals in place.
3. Pasted: treat pasted text as one item with source `pasted`.

The selected account is recorded in `config.md` during setup. Use only that integration; when it is set to intake-folder-only, skip mail and calendar access entirely.

## Processing (every item)

1. Summarize in 120 words or fewer.
2. Assign exactly one topic label from `taxonomy.md` (or a config.md extra topic).
3. Extract every deadline as YYYY-MM-DD with the verbatim source sentence.
4. Assign a priority: Urgent (deadline within 3 days or Chair-directed), High, Normal, Low.
5. Propose an owner and next action. Proposals only; the Chair confirms triage.
6. Propose a case link:
   - Same topic plus overlapping entities (unit, committee, person, project, budget line) plus an open case: link to that case.
   - High confidence: link automatically. Medium or low: the script attaches a review flag.
   - No open case matches: propose a new case with a one-line title.

## process payload schema

Write this JSON to `<root>/tmp/payload.json`, then run `process --root <root> --payload <root>/tmp/payload.json`:

```json
{
  "source": {"type": "email", "ref": "<message-id or subject+date>"},
  "received": "YYYY-MM-DD",
  "summary": "120 words or fewer",
  "topic": "Taxonomy label",
  "priority": "Normal",
  "deadlines": [{"date": "YYYY-MM-DD", "source": "verbatim sentence from the material"}],
  "case": {
    "action": "new",
    "id": "SC-2026-001",
    "title": "One-line title for a new case",
    "confidence": "high",
    "reason": "why this link or new case",
    "suggested_owner": "unit or person",
    "suggested_next_action": "one line"
  },
  "confidential": false
}
```

Rules: `source.type` is `email`, `file`, or `pasted` (a `ref` is required for email and file). For an existing case, set `action` to `existing` and include `id`; omit `title`. For a new case, set `action` to `new` and include `title`. Set `confidential` to true for any routing-guide topic.

## Triage

- Received: case exists, no confirmed owner or next action.
- Active: Chair confirmed owner and next action.
- Pending: waiting on another unit; `triage --status Pending` requires `--pending-unit`.
- Resolved: Chair confirms closure; record the resolution with `--next-action`.

## Board and briefing

- The board regenerates after every `process` and `triage`. To rebuild manually, run `board --root <root>`.
- When creating or updating the board, use the `ucsd-branding` skill to apply the current UCSD Decorator 5 shell.
- The interactive board supports inline case edits and drag-and-drop stage changes. Start it locally with `serve --root <root> --host 127.0.0.1 --port 8765`.
- Briefing data comes from `brief --root <root>`: deadlines within 7 days (including overdue), Pending cases by days waiting, Active cases untouched for 5+ days, and items received since the last briefing. Synthesize it into 200 words or fewer with two or three suggested first actions.
