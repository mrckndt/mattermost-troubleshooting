---
name: retro
description: Run a post-resolution retrospective on a resolved ticket - investigation retrospective, follow-up actions, KB-ingest decision, and public docs/KB review. Optional arg: ticket ID.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Run a post-resolution retrospective on a ticket.

## Phase 0 - Resolve ticket

1. Run `/resolve-ticket-id $ARGUMENTS` inline; ID returned: `<ID>` = that value.
2. Otherwise, if `$ARGUMENTS` contains a `tickets/<name>/` path reference and that directory exists: `<ID>=<name>`.
3. Otherwise, if this conversation has already been working a specific ticket (its files were read
   earlier in this session, e.g. via `/investigate`): use that `<ID>`.
4. Otherwise: ask the engineer for the ticket ID (or its `tickets/<name>/` path) before proceeding -
   this retrospective requires `tickets/<ID>/analysis.md` and can't be produced without a resolved
   ticket directory.

Save target: `tickets/<ID>/retro.md`.

## Prerequisites

This command runs **after** the investigation is complete — the root cause must be confirmed or
the ticket otherwise resolved. If `tickets/<ID>/analysis.md` is missing or its `Current hypothesis`
section is empty/says "unknown", stop and tell the engineer the ticket doesn't appear to be
resolved yet.

## Your task

Read `tickets/<ID>/analysis.md` and all other artifacts in the ticket directory. If `rca.md` or
`eir.md` exist, read those too. Then produce a retrospective that covers four areas:

1. **Investigation retrospective** — how did the investigation go?
2. **Follow-up actions** — what needs to happen now?
3. **KB ingest** — does this pattern belong in the knowledge base?
4. **Public docs & KB review** — should anything change at docs.mattermost.com
   or in the public support KB?

Write the output to `tickets/<ID>/retro.md`. After writing, print the full contents to the screen,
then print `Saved to: tickets/<ID>/retro.md`.

---

## Part 1 — Investigation retrospective

Review the investigation as captured in `analysis.md` and assess honestly:

### Blind triage effectiveness
- Did `/investigate`'s Phase 1 file inventory and error-families list surface the error(s) that
  turned out to be the root cause?
- If not — what was it about the error that made it hard to catch? Was it low
  volume, an unusual format, or buried in noise?
- Were there error patterns that dominated the triage but turned out to be
  irrelevant? Would a known-noise list have helped?

### Hypothesis path
- How many hypotheses were formed before landing on the root cause?
- Were any dead ends avoidable with better tooling or knowledge?
- Did anchoring on the customer's reported symptom delay finding the real cause?
- Was the root cause something the customer reported, something found in triage,
  or something discovered later through a different path?

### Artifact gaps
- What artifacts were available at the start vs. what was ultimately needed?
- Were there artifacts that had to be requested from the customer that could
  have been asked for earlier?
- Were any artifacts present but not useful? (e.g., logs from the wrong time
  window, redacted config)

### Time and effort
- How many sessions did the investigation span? (Count entries in `analysis.md`'s `Session log` section)
- Was the resolution path efficient, or were there significant detours?
- What single change would have shortened this investigation the most?

### Tooling observations
- Did the `/investigate` pipeline help or hinder for this type of issue?
- Are there specific error signatures or patterns from this ticket that
  `/investigate`'s Phase 1 inventory should be taught to recognize?
- Are there improvements to `/investigate`'s Phase 9 analysis-log template that would have helped?
- Should `/investigate`'s Phase 0-1 setup and inventory check for additional artifact types?

Be specific and evidence-based. Don't say "the investigation went well" — say
*what* went well and *why*. Cite sections of the analysis.

---

## Part 2 — Follow-up actions

Identify concrete follow-ups that should happen as a result of this ticket.
For each one, state clearly what the action is and why.

### Jira tickets
- Was a product bug confirmed? If so, does an existing Jira ticket cover it,
  or does one need to be filed?
- Was a misleading error message identified? That's worth a ticket.
- Was there a feature gap (missing config option, missing API, etc.) that
  contributed to the issue?

Use `mcp__claude_ai_Atlassian__*` (project `MM` only) to check for existing tickets before
recommending a new one. Use `mcp__claude_ai_GitHub_MCP__*` to check for existing issues or PRs.
Per `AGENTS.md`'s boundary: query both with generic technical terms only (error message templates,
function/symbol names, config keys) - never a customer's hostname, domain, email, username, org
name, or other identifying detail pulled from the ticket. If a tool is absent, state `GitHub search
skipped: MCP not available` / `Jira search skipped: MCP not available` and continue; never block.

### Documentation
- Was there a config value that behaves differently than documented or expected?
- Was there a deployment pattern (HA, air-gapped, etc.) that lacks guidance?
- Was an error message misleading enough that it should be documented or changed?

### Process improvements
- Should this class of issue be caught by a health check or monitoring?
- Is there a proactive communication we should send to customers on affected
  versions?
- Did the support workflow itself have a gap (e.g., missing escalation path,
  slow artifact collection)?

### Other
- Flag anything else that came up during the investigation that doesn't fit
  the above categories but still needs attention.

If there are no follow-ups in a category, omit that category entirely. Don't
pad with "none identified" sections.

---

## Part 3 — KB ingest

Decide whether this ticket's root cause belongs in the knowledge base.

### Decision criteria

**Create or update a KB entry when:**
- A bug in Mattermost code was found (will recur until fixed)
- A common misconfiguration was identified (multiple customers will hit it)
- A misleading error message was diagnosed (the diagnostic path is reusable)

**Skip KB ingest when:**
- The issue was purely customer-specific with no reusable diagnostic path
- The root cause is obvious from the error message alone (no diagnostic
  value in documenting the path)

### If creating or updating

Run `/kb-article <ID>` inline - it reads this ticket's `analysis.md`/`hub-thread.md`, resolves
ticket mode automatically, and writes/overwrites `tickets/<ID>/kb-article.md` + `.html`. Record in
`retro.md` which it did (new article vs. updated an existing one) and a one-line summary of the
pattern captured.

### If skipping

State why the pattern is not reusable. This goes in `retro.md` so the decision is recorded.

**Do NOT delete or modify the ticket's `analysis.md` — the KB distills it, does not replace it.**

---

## Part 4 — Public docs & KB review

Separate from the internal KB ingest in Part 3, evaluate whether this ticket
points to changes that should land in customer-facing documentation or the
public support knowledge base.

### a) docs.mattermost.com

Local mirror: `upstream/docs/source/`. Keep it aligned with the ticket's version per `AGENTS.md`;
use `/git-pull` (not raw git) if it needs refreshing. Public site: https://docs.mattermost.com.

Ask:
- Is there a config setting, behavior, or deployment pattern in this ticket
  that is undocumented, incorrectly documented, or under-documented?
- Was the customer's confusion traceable to docs that are ambiguous, stale,
  or missing a warning/note?
- Is there an error message or symptom that doesn't appear anywhere in the
  docs and should?

If yes, propose a specific change: which page, what edit. Grep `upstream/docs/source/` to confirm
current state before recommending — do not assume a page is missing without checking.

### b) Public support KB — new article candidate

Public KB: https://support.mattermost.com.

Ask:
- Is the resolution something a customer could self-serve on if they hit it
  again? (config fix, known limitation, version-specific gotcha)
- Is the diagnostic path generic enough that other customers would benefit?
- Would a public article reduce future ticket volume for this pattern?

Before searching `support.mattermost.com` (WebFetch/WebSearch), apply the same generic-terms-only
query boundary from `AGENTS.md` as Part 2's Jira/GitHub lookups.

If yes, draft a proposed title and a 2-3 sentence summary of what the article should cover. The
actual article goes through the support team's normal publishing process — the retro just
identifies the candidate.

### c) Public support KB — existing article check

Search the public KB for the error signature, symptom, or feature area (same query-boundary rule
as (b)).

- If an article already exists: does it match what was actually found in this
  ticket? Are there missing error variants, missing version coverage, or an
  out-of-date fix? Propose specific edits.
- If no article exists: this loops back to (b) — note it as a candidate.

If you cannot access the public KB directly, say so and flag the search terms
the support team should check manually.

### Skip when

- Issue was a one-off product bug already filed and being fixed (no customer
  workaround worth documenting)
- Root cause was customer-environment specific with no transferable guidance
- Pattern is already well-covered in both docs and KB (note this — it's a
  positive signal worth recording)

---

## retro.md format

```markdown
# Ticket <number> — Retrospective

**Date:** <today's date>
**Resolution:** <one-line summary of root cause and fix>

---

## Investigation retrospective

### Blind triage
<!-- Did it catch the root cause? What was missed and why? -->

### Hypothesis path
<!-- How many hypotheses? Dead ends? Was anchoring a factor? -->

### Artifact gaps
<!-- What was missing? What should have been requested sooner? -->

### Efficiency
<!-- Sessions, detours, what would have shortened the investigation -->

### Tooling observations
<!-- What should change in the /investigate pipeline or workflow? -->

---

## Follow-up actions

<!-- Only include categories that have actual items -->

### Jira tickets
- [ ] <action> — <reason>

### Documentation
- [ ] <action> — <reason>

### Process improvements
- [ ] <action> — <reason>

---

## KB ingest

**Decision:** <added via /kb-article / updated via /kb-article / skipped>
<!-- If added/updated: what was changed. If skipped: why. -->

---

## Public docs & KB review

### docs.mattermost.com
<!-- Specific page + proposed edit, or "no changes needed" with brief reason -->

### Public KB — new article candidate
<!-- Proposed title + 2-3 sentence scope, or "not a candidate" with brief reason -->

### Public KB — existing article
<!-- Article URL/title found + proposed edits, or "no existing article" / "existing article is accurate" -->
```

---

## Tone and style

- Be honest and specific. This is an internal process improvement tool, not
  a customer-facing document.
- Don't soften findings. If the investigation took a wrong turn, say so and
  say why.
- Focus on systemic improvements, not one-off observations. "We should add
  X pattern to the triage step" is more useful than "this was a tricky ticket."
- Every observation should point toward a concrete action or a decision that
  it's not worth acting on.
