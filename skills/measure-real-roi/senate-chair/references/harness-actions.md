# Harness Actions

These prompts are the local action surface after installation. The default skill chip uses the first prompt.

## Initialize and process

```text
Use $senate-chair to initialize my data root and process new materials.
```

1. Verify the model policy first.
2. If `python3 scripts/senate_chair.py status` reports an uninitialized root, ask only for:
   - the email link: `Gmail`, `Outlook`, or `Intake folder and pasted text only`
   - the data root, defaulting to `~/SenateChair`
3. Run one command, substituting the Chair's choices:

```bash
python3 scripts/senate_chair.py setup --root <root> --account <gmail|outlook|none> [--account-address <address>]
```

4. Continue directly into the normal intake workflow. If the Chair did not choose an email link, use only the intake folder and pasted text.

## View board

```text
Use $senate-chair to view my board.
```

Run:

```bash
python3 scripts/senate_chair.py board
```

Then open `<root>/board/index.html` locally. In TritonAI Harness, use the collaborative preview browser when available; on macOS, `open <root>/board/index.html` also works. For drag-and-drop editing, use `serve` and keep the server bound to `127.0.0.1`.

## Daily briefing

```text
Use $senate-chair to run my daily briefing.
```

Run:

```bash
python3 scripts/senate_chair.py brief
```

Synthesize the returned JSON into 200 words or fewer, include two or three suggested first actions, save it to `<root>/briefings/YYYY-MM-DD.md`, and show it.

## Status

```text
Use $senate-chair to show my setup status.
```

Run:

```bash
python3 scripts/senate_chair.py status
```

The remembered root is stored in `~/.senate-chair/root`. That pointer contains only the local path, never Chair content. Override it for one command with `--root` or for a session with `SENATE_CHAIR_ROOT`.
