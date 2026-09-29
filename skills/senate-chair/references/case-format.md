# Case and Item Formats

The script owns these formats. Read them to understand the store; do not edit case or item files by hand — use the `process`, `triage`, and `mark` commands so IDs, logs, and the board stay consistent.

## case.md

```markdown
# SC-2026-001: <one-line title>
- Status: Received | Active | Pending | Resolved
- Topic: <taxonomy label>
- Owner: <name or unit, or "unassigned">
- Suggested owner: <proposal awaiting triage>
- Opened: YYYY-MM-DD
- Last update: YYYY-MM-DD
- Next action: <one line, or "awaiting triage">
- Review flag: <blank | new case unreviewed | auto-link medium confidence | auto-link low confidence>
- Pending unit: <unit being waited on>
- Pending since: YYYY-MM-DD
- Confidential: yes | no

## Deadlines
| Deadline | Source sentence | Item | Done |
|---|---|---|---|
| 2026-10-15 | "comments are due October 15" | 2026-09-29-001 | no |

## Log
- YYYY-MM-DD: <what changed>

## Items
- 2026-09-29-001: <one-line summary>
```

## Item file

```markdown
# Item 2026-09-29-001
- Source: email <message-id> | file <path> | pasted
- Received: YYYY-MM-DD
- Case: SC-2026-001
- Topic: <label>
- Priority: Urgent | High | Normal | Low
- Link confidence: high | medium | low — <one-line reason>

## Summary
<120 words or fewer>

## Deadlines
- YYYY-MM-DD: <verbatim source sentence>
```

## Commands

- `init --root <path>`: create the data root, folders, and `config.md`.
- `process --root <root> --payload <json>`: persist one processed item; create or update its case; regenerate the board.
- `triage --root <root> --case <id> [--status <s>] [--owner <o>] [--next-action <text>] [--pending-unit <unit>] [--clear-review]`: apply Chair-confirmed decisions; regenerate the board.
- `board --root <root>`: regenerate `board/index.html`.
- `brief --root <root> [--date YYYY-MM-DD]`: print the briefing JSON skeleton and update the last-briefing marker.
- `list --root <root> [--status <s>] [--topic <t>]`: list cases.
- `mark --root <root> --mail-run YYYY-MM-DD`: record the last processed mail date.
