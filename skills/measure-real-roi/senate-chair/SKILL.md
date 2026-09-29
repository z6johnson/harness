---
name: senate-chair
description: Set up and run Senate Chair operations. Select the Chair's own Gmail or Outlook link, initialize a local data root, intake materials from email, an intake folder, or pasted text; summarize and label them; extract deadlines; manage cases on a Kanban board; generate a daily deadline-and-bottleneck briefing; draft replies from an approved answer bank; and manage the Chair's calendar. Use when the Senate Chair or delegate asks to initialize the system, process new materials, view the board, run the briefing, triage or find a case, draft a reply, or handle scheduling.
---

# Senate Chair

A local-first operations system for the Senate Chair: intake, case management, a visual board, and a daily briefing, with reply drafting and scheduling as case actions. The skill acts only on the Chair's personal connected account and only on approved on-prem models.

## Model Policy

1. Read `references/model-policy.md` first. Verify the session's selected model is on the approved on-prem list before touching any Chair content. If it is not, stop and name the approved models.

## Quick Start

Use `references/harness-actions.md` for the installed action prompts.

1. **Initialize.** If `python3 scripts/senate_chair.py status` reports no initialized root, ask for the email link (`Gmail`, `Outlook`, or intake-folder-only) and root location (default `~/SenateChair`). Then run `python3 scripts/senate_chair.py setup --root <root> --account <gmail|outlook|none>`. Setup records the account label, remembers the root, and generates the board.
2. **Process.** Continue directly into intake. If the linked account is Gmail or Outlook, use only that Chair-owned integration; otherwise use `<root>/intake/` and pasted text.
3. **Board.** Run `python3 scripts/senate_chair.py board`, then open `<root>/board/index.html` locally. For drag-and-drop edits, run `serve` bound to `127.0.0.1`.
4. **Briefing.** Run `python3 scripts/senate_chair.py brief`, synthesize the JSON into 200 words or fewer, save it to `<root>/briefings/YYYY-MM-DD.md`, and show it.

The remembered root is `~/.senate-chair/root`. Commands accept `--root` or `SENATE_CHAIR_ROOT` when a different root is needed.

## Workflow

1. **Intake.** Read `references/workflow.md`. Collect new materials from the Chair's own mailbox (per `references/account-access.md`), new files in `<root>/intake/`, and pasted text. Each material becomes one item. After processing mail, record the timestamp with `python3 scripts/senate_chair.py mark --root <root> --mail-run YYYY-MM-DD`.
2. **Process.** For each item, produce a summary of 120 words or fewer, one topic label from `references/taxonomy.md`, every deadline normalized to YYYY-MM-DD with its verbatim source sentence, a priority, a suggested owner, and a proposed case link. Write the payload to `<root>/tmp/payload.json` using the schema in `references/workflow.md`, then persist it with `python3 scripts/senate_chair.py process --root <root> --payload <root>/tmp/payload.json`.
3. **Cases.** New issues open new cases in `Received`; updates append to existing cases. Apply the Chair's triage decisions with `python3 scripts/senate_chair.py triage --root <root> --case <id> ...` per `references/case-format.md`.
4. **Board.** The script regenerates the dashboard after every change. Apply the current UCSD Decorator 5 shell using the `ucsd-branding` skill, then give the Chair the path to `<root>/board/index.html`. To regenerate manually: `python3 scripts/senate_chair.py board`. To use the interactive board, run `python3 scripts/senate_chair.py serve --host 127.0.0.1 --port 8765`.
5. **Briefing.** Run `python3 scripts/senate_chair.py brief`, synthesize the returned JSON into a briefing of 200 words or fewer, save it to `<root>/briefings/YYYY-MM-DD.md`, and show it.
6. **Actions.** Draft replies from `references/answer-bank.md` in the Chair's voice using `references/voice.md` and `assets/reply-template.md`; save unsent drafts only, and log the draft in the case. Handle scheduling per `references/account-access.md`; the Chair confirms every event change.

## Hard Rules

- On-prem models only: never process Chair mail, calendar, case, or answer-bank content on a model outside the approved list in `references/model-policy.md`.
- Own account only: never a shared, delegated, or departmental mailbox or calendar.
- Store only the account label and optional display address during setup; never store credentials or OAuth tokens.
- Never send email or invitations. Unsent drafts and Chair-confirmed calendar changes only.
- All case data stays under the Chair's data root. Never upload Chair content to any external service.
- Keep the board local. Serve it only on `127.0.0.1`; never expose it on a network interface.
- Do not fabricate deadlines, owners, or case links. Every extracted deadline cites its verbatim source sentence.
- Flag medium- and low-confidence case links for review instead of blocking intake.
- Only `references/answer-bank.md` is authoritative for Senate answers. Do not invent policy, timelines, or procedures. An empty or incomplete bank means "no match," not permission to improvise.
- If an answer-bank entry's last-reviewed date is more than 12 months old, flag it "verify before use" and show the date.
- For any topic in `references/routing.md`, create the case, mark it confidential and routed, and draft at most a brief acknowledgment.
- Keep message content out of any file outside the data root unless the Chair explicitly asks to save a new answer-bank entry.
- Use placeholders such as `[Faculty member]` for names in drafts unless the message itself establishes the name the Chair uses.
