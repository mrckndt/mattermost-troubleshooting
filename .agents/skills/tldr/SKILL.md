---
name: tldr
description: Print a concise tl;dr for a ticket (ID or URL) or for arbitrary pasted text. Reads the ticket's analysis.md if present; runs /investigate first if the ticket has no analysis.md yet.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

## Phase 0 - Resolve argument type

1. **No `$ARGUMENTS`:**
   - If this conversation already contains an investigation conclusion (a completed `/investigate` run, or the most recent substantive assistant message states a diagnosis, root cause, fix, or resolution): **session mode**.
   - Otherwise: ask for a ticket ID/URL or text before proceeding.
2. `$ARGUMENTS` matches an existing directory under `tickets/` (check with `ls "$PROJECT_ROOT/tickets/$ARGUMENTS"`): **ticket mode**, `<ID>=$ARGUMENTS`.
3. `$ARGUMENTS` looks like a URL (`http://` or `https://`): extract the trailing numeric path segment as a candidate ID (e.g. `.../tickets/51427` -> `51427`). If `tickets/<candidate>/` exists: **ticket mode** with that ID. Otherwise fall through to step 4 - do not fabricate a ticket folder.
4. Otherwise: **text mode**, treat `$ARGUMENTS` as the markdown text to summarize.

## Ticket mode

1. If `tickets/<ID>/analysis.md` exists, read it.
2. If it does not exist, state:
   ```
   tickets/<ID>/analysis.md not found - running /investigate <ID> first.
   ```
   then run `/investigate <ID>` inline, then read the resulting `tickets/<ID>/analysis.md`.
3. Condense the file's current state into the output format below. Pull from `Reported symptom`, `Current hypothesis`, `Steps and outcomes`, `Resolution`, and `Next steps` (current template), or `Issue summary and environment` / `Investigation` / `Current hypothesis` for legacy-template tickets (no `Reported symptom`/`Resolution` headings).

## Text mode

Summarize `$ARGUMENTS` directly. Do not invoke `/investigate` for text input - condense what's given, nothing more.

## Session mode

Summarize the current conversation's most recent investigation conclusion directly - no file lookup, no `/investigate` call. Treat the conversation itself as the source text, same as text mode.

## Output format

Apply the formatting constraints from `AGENTS.md` (no em dashes; code fences for commands, config keys, file paths, values).

Ticket mode:
```
**TL;DR (Ticket <ID>):** <symptom>; <root cause or leading hypothesis>; <fix or next step>. Status: <open | resolved | blocked on <X>>. (source: tickets/<ID>/analysis.md)
```

Text and session mode (drop the ticket qualifier and source line):
```
**TL;DR:** <summary in the same shape>.
```

Rules:
- 2-4 sentences, no filler.
- If unresolved, end on the concrete next step, not a vague "still investigating."
- State uncertainty briefly rather than omitting it, per AGENTS.md tone rules.
