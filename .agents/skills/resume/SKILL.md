---
name: resume
description: Resume an in-progress ticket investigation. Reads analysis.md and analysis-full.md, reconstructs session context, identifies the last completed phase, and continues from the next one.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

## Phase 0 - Resolve ticket ID

If `$ARGUMENTS` matches a directory under `tickets/`, set `<ID>=$ARGUMENTS`. Otherwise list `tickets/` subdirectories and ask which ticket to resume before proceeding.

## Phase 1 - Reconstruct context

If `tickets/<ID>/analysis.md` does not exist, state `tickets/<ID>/analysis.md not found - running /investigate <ID> from Phase 0` and run `/investigate <ID>` instead of continuing below.

Read both files:
- `tickets/<ID>/analysis.md`
- `tickets/<ID>/analysis-full.md`

Emit a structured session briefing:

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

## Phase 2 - Identify resume point

Determine the last completed phase by reading the analysis log:
- If "Next steps" names a specific phase (e.g. "run Phase 6 docs search"), resume from that phase.
- If "Resolution" is populated, the ticket is closed - confirm with the engineer before continuing.
- If unclear: default to Phase 7 if "Evidence collected" or "Current hypothesis" is non-empty in `analysis.md` (phases 5-6 are likely done); otherwise default to Phase 5. State the assumption either way.

State: "Resuming from Phase <N> - <phase name>."

## Phase 3 - Continue investigation

Follow the rules for the identified phase as defined in `/investigate` inline - do not re-invoke the skill from Phase 0. Append a new session entry to `analysis-full.md`:

```
---
## Session <YYYY-MM-DD>
Resumed from Phase <N>.
```
