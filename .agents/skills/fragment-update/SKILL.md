---
name: fragment-update
description: Draft and write fragment updates from current ticket findings. Reads Phase 8 fragment opportunity notes and analysis.md, drafts new or updated sections in the established fragment format, presents a diff for approval, then writes on confirmation.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

## Phase 1 - Gather inputs

1. Identify in-scope repos: read the current conversation for Phase 8 `Fragment opportunity` or `Fragment update opportunity` statements. If none are present, check `tickets/<ID>/analysis.md` (ask for `<ID>` if not clear from context).
2. For each in-scope repo, check whether `fragments/<repo>.md` exists and read it in full if so.
3. Pull the specific patterns, `file:line` references, and quoted log lines cited in the fragment opportunity notes. If the notes are vague and lack citations, search for them now: `rg`/`grep` the pattern or error string in `upstream/<repo>/` and add the `file:line` reference before proceeding to Phase 2.

If no fragment opportunity notes can be found and no ticket context is available, ask the engineer to describe the pattern to capture before proceeding.

## Phase 2 - Draft update

For each in-scope repo, draft the new or updated content:

- **New fragment:** draft a stub with the repo name as a top-level heading and the new section below it.
- **Existing fragment:** draft only the new or changed section(s); do not re-emit unchanged content.

Follow the fragment format from `AGENTS.md` editing conventions:
- Headings in sentence case; `fragments/<repo>.md` sections at `###`, sub-topics at `####`.
- Bullets for enumerable items; prose for explanation.
- `**Label:**` to lead bullets naming concepts.
- Every claim backed by `file:line` or a quoted log line. No general advice that upstream docs already cover.

Present the draft as a clearly labelled diff:

```
### Fragment: fragments/<repo>.md

#### New section: <section title>
<drafted content>
```

Ask for approval before writing. Do not write until confirmed.

## Phase 3 - Write

On approval, `Edit` or `Write` the fragment file(s). Confirm with a one-line summary of what was written.
