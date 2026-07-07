---
name: kb-batch
description: Bulk-draft KB articles for a TSE's assigned Zendesk tickets in a time window. Harvests Hub threads via /hub-harvest, drafts one article per ticket with /kb-article, then walks you through proofreading one at a time. Resumable.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Turn a window of a TSE's assigned tickets into KB-article drafts on disk, then proofread
them one at a time. This skill orchestrates two existing skills - `/hub-harvest` (fetch)
and `/kb-article` (draft) - and owns the manifest that tracks draft/review state so a run
can be interrupted and resumed.

`$ARGUMENTS` = assignee email plus an optional time range or free-text scope hint (same
parsing as `/hub-harvest` assignee mode). If empty, ask for an assignee email before
proceeding.

## Phase 0 - Setup

1. Confirm the Mattermost Hub MCP is present (`mcp__claude_ai_Mattermost_Hub__*`). If
   absent, state `Mattermost Hub search skipped: MCP not available` and stop. Never block.
2. Parse `$ARGUMENTS`: the `@` token is the assignee email; the remainder is the time range.
   Resolve it to `[since, until]` the same way `/hub-harvest` does (explicit range, natural
   language, or a 30-day default). Echo the resolved window.
3. Compute `<emaillocalpart>` (the email before `@`) and today's date. These name a fresh
   manifest in Phase 1; an existing in-progress manifest is found by assignee, not by date.

## Phase 1 - Harvest (delegate)

Look for existing manifests matching `tickets/kb-batch/<emaillocalpart>-*.md`, regardless of date.
- **None exist:** **fresh run.** Compute the run key `<emaillocalpart>-<YYYY-MM-DD>` (today) and
  run `/hub-harvest <assignee email> <range>` inline to populate `tickets/<zd#>/hub-thread.md`
  for every in-window thread and write the harvest index `tickets/hub-harvest/<run key>.md` (mirrors
  how `/tldr` runs `/investigate` first). Then read that harvest index for the ticket list,
  statuses, and `analysis?` flags. If the harvest finds no threads, say so and stop.
- **One or more exist and the most recent is not fully terminal** (has any row not
  `approved`/`edited`/`deferred`): **resume that same file** - its filename stem (whatever
  date it carries) is this run's `<run key>` for the rest of the pipeline; do not rename it
  or create a new one. Do not re-harvest and do not re-draft rows already `drafted`/`thin`/
  `skipped`/`approved`/`edited`/`deferred`. Skip to Phase 4 at the first non-terminal row. Optionally
  offer to run `/hub-harvest` again (window ending today) to pick up tickets that arrived
  since the last run; if so, append any newly-discovered tickets as new rows to this same
  manifest file rather than creating a second one, and never touch the review state of
  existing rows.
- **One or more exist and the most recent is fully terminal** (every row `approved`/`edited`/
  `deferred`): **refresh run.** Reuse that same manifest file - its filename stem stays this
  run's `<run key>`, unchanged; never create a second manifest for the same assignee. Read its
  `Window:` header line for the recorded `since`. Echo the actual refresh window (`<since>` to
  today; this may override what Phase 0 echoed from `$ARGUMENTS`, since the refresh window
  always keeps the original `since`). Run `/hub-harvest <assignee email> <since>..<today>`
  inline (`<today>` is the date from Phase 0) to refresh `tickets/<zd#>/hub-thread.md` for
  every in-window thread; this writes a fresh harvest index named by today's date
  (`tickets/hub-harvest/<emaillocalpart>-<today>.md`, which may differ from `<run key>` if the
  manifest predates today) carrying a `Change` column (`new`/`updated`/`unchanged`) per
  ticket. This re-harvest is automatic, not gated behind a confirmation question. Proceed to
  Phase 2 to reconcile the fresh index against the existing manifest rows; do not skip
  straight to Phase 4.

## Phase 2 - Manifest

This file is the resumability backbone; keep it current as drafting and review progress.

**Fresh run.** Create `tickets/kb-batch/<run key>.md` from the harvest index: one row per ticket,
grouped by status, seeded to review state `pending-draft`.

```
# KB batch - <assignee email> - <today>

Window: <since> to <until>. Harvest index: tickets/hub-harvest/<run key>.md. Threads: <N>.
Review states: pending-draft -> drafted | thin -> approved | edited | deferred | skipped
(skipped rows are re-presented on the next run).

## <Status>

| zd# | Subject | analysis? | Draft | Review |
|---|---|---|---|---|
| <zd#> | <subject> | yes/no | tickets/<zd#>/kb-article.md | pending-draft |
```

A manifest may also carry a freeform section, introduced by a line starting `Reviewer flags`
(not a markdown heading; optionally followed by a parenthetical, then a colon), placed between
the header lines and the first `## <Status>` section, for one-off human-readable notes (for
example a dedup warning, or a reopened-row note from the refresh-run reconciliation below). Add
this section, with that exact leading label, if it does not already exist.

**Refresh run - reconcile.** Only on the refresh-run branch from Phase 1. First, update the
manifest header in place: set `until` to today (`since` stays as originally recorded), point
`Harvest index:` at the fresh index just written, and update `Threads: <N>` to the new total row
count. Then, for each ticket in the fresh harvest index, use its `Change` column to decide what
happens to the corresponding manifest row. If a ticket's current status differs from the section
its row is currently filed under, move the row to the matching `## <Status>` section so the
manifest stays grouped by status, matching the harvest index.

- **`new`, no existing row for that zd#** - append a new row, `Review` = `pending-draft` (same
  as a fresh run).
- **`unchanged`, an existing row for that zd#** - leave that row completely untouched; do not
  read or rewrite it.
- **`unchanged`, no existing row for that zd#** (the manifest predates the `Change` column, or
  the ticket fell out of a prior window and is back) - add it as a new row, `Review` =
  `pending-draft`; this pipeline has never drafted it, regardless of the `unchanged` label.
- **`updated`, existing row is non-terminal** (`pending-draft`/`drafted`/`thin`/`skipped`) - set `Review`
  = `pending-draft` and refresh the row's `analysis?` value from the harvest index, so Phase 3
  redrafts it with the fresh content. No reviewer-facing note is needed; the reviewer never saw
  the stale draft.
- **`updated`, existing row is terminal** (`approved`/`edited`/`deferred`, treated uniformly -
  no state gets special-cased) - reopen it: set `Review` = `pending-draft`, refresh
  `analysis?` from the harvest index, and append a bullet to the `Reviewer flags` section
  recording the prior state: `` - **<zd#>**: was `<prior state>` as of <today>, thread updated
  since - re-review before republishing. `` Reuse this existing freeform section; do not add a
  new column or a new `Review` value.

A row whose ticket is absent from the fresh harvest index entirely (window moved past it, or it
was reassigned away from this TSE) is left untouched; never delete a row.

## Phase 3 - Auto-draft (every thread, all states)

Draft every harvested thread regardless of `Current Status` (Open / Pending / Solved /
Closed). Nothing is skipped for state. A `pending-draft` row may be brand new or reopened
(reset by Phase 2 reconciliation because its thread changed since a prior terminal decision);
both are drafted the same way. For each `pending-draft` row, in manifest order:

1. Read `tickets/<zd#>/hub-thread.md`, and `tickets/<zd#>/analysis.md` (or
   `analysis-full.md`) if the row is `analysis? yes`, so both are in context.
2. Invoke `/kb-article` inline with an argument that names the ticket and points at those
   files, e.g. `` /kb-article Ticket <zd#> (<subject>). Draft from
   tickets/<zd#>/hub-thread.md and tickets/<zd#>/analysis.md if present. ``. This puts the
   ticket dir in `/kb-article`'s own "review ./tickets/<name>/ files" scope; the argument
   keeps it focused on this one ticket.
3. **Do not stall the batch.** If `/kb-article` would ask a clarifying follow-up, proceed
   with the available context instead; a ticket with no resolution yet (for example an Open
   thread with no analysis) still gets whatever article the thread supports.
4. Capture `/kb-article`'s two outputs and write them immediately (no data loss):
   - the Markdown article (including its `##` topic heading) -> `tickets/<zd#>/kb-article.md`
   - the HTML (the contents of the `# 📋 Article HTML` block, without the outer ``` fence)
     -> `tickets/<zd#>/kb-article.html`
5. Update the row: `Draft` = `tickets/<zd#>/kb-article.md`, `Review` = `drafted`, or `thin`
   if the source thread had no resolution and no analysis to draw on (flag it so the reviewer
   prioritizes it).

Only ever add `hub-thread.md` / `kb-article.md` / `kb-article.html` to a ticket dir. Never
edit or delete a pre-existing file there (`analysis*.md`, raw customer files).

After drafting, do not re-quote the articles in the reply; the files are the record. Report
a one-line count (drafted / thin) and move to review.

## Phase 4 - Review (one at a time)

Walk the reviewer through the `drafted`, `thin`, and `skipped` rows in manifest order, one
ticket per step. For each:

1. Show: zd#, subject, status, review state, draft path, then print the full Markdown of
   `tickets/<zd#>/kb-article.md` (not a summary - the reviewer is proofreading, and a
   summary hides exactly the wording they need to check). If the `Reviewer flags` section has
   a bullet naming this zd#, print it first, so the reviewer knows this is a re-review, not a
   first pass.
2. Ask for a decision:
   - **approve** -> set `Review` = `approved`.
   - **edit** (reviewer describes changes) -> apply them to `tickets/<zd#>/kb-article.md`,
     regenerate `tickets/<zd#>/kb-article.html` to match, set `Review` = `edited`.
   - **defer** -> set `Review` = `deferred`, move on.
   - **skip** -> set `Review` = `skipped`; move to the next row without re-presenting it in
     this pass. Unlike `defer` (permanent), a skipped row stays non-terminal and is
     re-presented the next time `/kb-batch <same assignee>` runs (later in a resumed session
     or a future day) - use this to put a ticket off for now rather than decide against it.
   - **recreate** -> redraft via Phase 3 steps 2-4 directly, then re-present. Use when the
     draft is off but the source material (`hub-thread.md`, existing `analysis.md`) doesn't
     need deeper investigation. If the ticket needs a fresh `/investigate` pass, run it
     yourself outside this flow, then choose `recreate` to pick up the refreshed
     `analysis.md`; running `/investigate` inline here would block the review loop for the
     length of a full investigation (10+ minutes).
3. Write the manifest after each decision so state survives an interruption.

Stop when every row is `approved`, `edited`, or `deferred`; a row left `skipped` keeps the
manifest non-terminal, so it's picked up again on the next run. Rerunning `/kb-batch <same
assignee>` any day thereafter, before every row is terminal, resumes the same manifest at
the first non-terminal row without re-fetching or re-drafting; rerunning it after every row
is terminal instead starts a refresh run that reopens only the rows whose threads changed
(see Phase 1).

## Phase 5 - Summarize

Report: the manifest path, counts by final review state (approved / edited / deferred /
skipped / thin), and the list of finalized article paths (`tickets/<zd#>/kb-article.md` +
`.html`) ready to publish. Any remaining `skipped` rows mean the batch isn't fully done yet.
On a refresh run, also report how many rows were reopened in Phase 2 (thread updated since a
prior approve/edit/defer) and how many of those are finalized again now.
