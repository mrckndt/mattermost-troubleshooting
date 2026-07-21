---
name: resume-investigation
description: Resume a ticket investigation: read analysis.md/analysis-full.md, ask before running /investigate; skip the ask only if no analysis files exist.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

## Phase 0 - Resolve ticket ID

Run `/resolve-ticket-id $ARGUMENTS` inline; ID returned: set `<ID>` to that value. Otherwise list `tickets/` subdirectories and ask which ticket to resume.

## Phase 1 - Reconstruct or start

- Neither `analysis.md` nor `analysis-full.md` exists: state `tickets/<ID>/analysis.md not found - running /investigate <ID> from Phase 0` and run `/investigate <ID>`.
- This is the only case where `/investigate` runs without asking first.
- Otherwise, read whichever of `analysis.md`, `analysis-full.md` exist, then emit a structured session briefing:

```
## Resuming ticket <ID>

**Ticket type:** <Fault investigation | Advisory / research>
**Deployment:** <version, type, DB, method>
**Reported symptom:** <one line>
**Artifacts reviewed:** <list>
**Current hypothesis:** <one line>
**Ruled out:** <list>
**Open questions:** <list>
**Next steps:** <list>
```

## Phase 2 - Ask before investigating

- `Resolution` populated: note the ticket is closed.
- Ask: `Context reconstructed from <files read>. Run a new /investigate <ID>?`
- Run `/investigate <ID>` inline (primed with `Next steps`/`Open questions`) only if the engineer says yes; otherwise stand by.
