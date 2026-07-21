---
name: resume-investigation
description: Resume a ticket investigation. Reads analysis.md and analysis-full.md to reconstruct context if present; otherwise runs a fresh /investigate.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

## Phase 0 - Resolve ticket ID

Run `/resolve-ticket-id $ARGUMENTS` inline; ID returned: set `<ID>` to that value. Otherwise list `tickets/` subdirectories and ask which ticket to resume.

## Phase 1 - Reconstruct or start

- If `tickets/<ID>/analysis.md` does not exist: state `tickets/<ID>/analysis.md not found - running /investigate <ID> from Phase 0` and run `/investigate <ID>` instead of continuing below.
- If it exists: read it and `tickets/<ID>/analysis-full.md`, then emit a structured session briefing:

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

## Phase 2 - Continue or stop

- If `Resolution` is populated, the ticket is closed - confirm with the engineer before continuing.
- Otherwise, run `/investigate <ID>` inline for a new session, primed with `Next steps`/`Open questions` above.
