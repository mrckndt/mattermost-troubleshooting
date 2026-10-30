---
name: hub-harvest
description: Fetch a Zendesk ticket thread (by ticket ID, assignee email for a time window, or a pasted Hub thread permalink) from the Mattermost Hub into tickets/<zd#>/zendesk-thread.md (migrates a legacy hub-thread.md). Ready for /investigate.
user-invocable: true
---

Args: $ARGUMENTS

Fetch Zendesk ticket conversations from the Mattermost Hub and persist each one to disk once,
so later work (`/investigate`) reads from `tickets/<zd#>/` instead of re-querying
the Hub.

- **Source:** fixed Hub channel `p77n3165i3r89kugxyabx9wwer` ("Zendesk Notifications", team Staff).
- **Thread shape:** one thread per ticket - a root `New Ticket: <subject> (#zdNNNNN)` post plus threaded replies.
  The root post's own ID is the thread `Root ID`.
- **Worker:** each thread is fetched, derived, filtered, and written by one `hub-thread-harvester` subagent
  (`agents/thread-harvester.md`, next to this file). That file owns derivation, the assignee filter, change
  classification, persistence, and the template; `AGENTS.md` § Subagent handoffs owns its return line.

## Phase 0 - Setup and mode

1. Confirm the Mattermost Hub MCP is present (`mcp__claude_ai_Mattermost_Hub__*`). If absent,
   state `Mattermost Hub search skipped: MCP not available` and stop. Never block.
2. If `$ARGUMENTS` is empty, ask for a ticket number, an assignee email, or a Hub thread link before proceeding.
3. Pick the mode, in this order:
   - `$ARGUMENTS` matches `https?://\S+/pl/([A-Za-z0-9]{26})` (a Mattermost permalink, any host -
     `<siteURL>/<team-name>/pl/<postID>`): **link mode**, the captured group is the entry post ID.
   - An `@` token: **assignee mode** (that token is the email, the remainder is the time range).
   - Otherwise **ticket mode**: if `<the remainder>` is already a bare ticket number (`AGENTS.md`'s ID
     format contract), set `<ID>` to it directly and skip to Phase 1. Otherwise, apply `/resolve-ticket-id`'s
     normalization rules (steps 1-2 in `.agents/skills/resolve-ticket-id/SKILL.md`) to `<the remainder>`
     directly, in this same reasoning step - do not invoke it as a nested skill call. A missing
     `tickets/<candidate>/` is not a failure here (equivalent to that skill's `--allow-new`). Set `<ID>` to
     the resolved candidate, continue to Phase 1.
4. Note today's date (`YYYY-MM-DD`); every worker prompt carries it.

## Phase 1 - Locate roots

**Link mode skips this phase entirely** - the entry post ID from Phase 0 goes straight to Phase 2; the worker
resolves the true root.

Use `mcp__claude_ai_Mattermost_Hub__search_posts` with `channel_id` set to
`p77n3165i3r89kugxyabx9wwer`. Keep `keyword_limit`/`semantic_limit` at their defaults; raising
them risks an oversized result truncated to a file.

**Ticket mode.** Query the ticket number (bare and `zd<num>` forms). The `Root ID` is the `Post ID` of the `New
Ticket: ... (#<num>)` post whose subject ends in exactly `(#<num>)`; a root of another ticket that merely mentions
`#<num>` (e.g. `RE: #<num>: ...`) doesn't count. If none matches, state `no New Ticket post found for #<num>` and
stop.

**Assignee mode.**
1. Resolve `[since, until]` from the remainder of `$ARGUMENTS`: an explicit
   `YYYY-MM-DD..YYYY-MM-DD` range, a natural-language phrase (`last 2 weeks`, `June`), or, absent
   any time expression, a 30-day lookback ending today. Echo the resolved window before fetching.
2. Resolve the assignee's display name via `mcp__claude_ai_Mattermost_Hub__search_users`, querying the email's
   local part (before `@`) - the full email address does not match. Success: use the returned name. Failure or
   empty result: fall back to title-casing the local part (`firstname.lastname` -> `Firstname Lastname`).
   Discovery/signature-matching aid only, never ground truth by itself - the worker's filter still decides.
3. Query the assignee email, then separately query the resolved display name. Page each with
   `keyword_offset` until a page returns no new posts. Collect and dedup every result's `Root ID`
   from both queries into one candidate set - the name query catches a thread that never shows the
   email string in its text, instead of relying on coincidental token overlap with the email query.
4. **Search is discovery, not ground truth - do not filter here.** A hit only proves a query
   matched somewhere in that post; it is never authoritative for a structured field like
   `Current Assignee`. Keyword mode further tokenizes on non-alphanumeric characters, so an
   email-shaped query (`firstname.lastname@...`) becomes an AND of `firstname` and `lastname`,
   matching any post where both co-occur anywhere in the text (a signature, a quoted email) -
   not only a post whose `Current Assignee` field literally holds that address. A hit also need
   not be a thread's newest post; the real filter runs in the worker, against a full-thread fetch.

## Phase 2 - Dispatch workers

1. Dedupe the post IDs (Root IDs, or the link-mode entry post ID).
2. Launch one `hub-thread-harvester` per post ID, all in one message; above 10 IDs, in batches of 10. Each prompt
   carries: post ID, mode, project root, today, and in assignee mode the email, the display name from Phase 1, and
   `[since, until]`.
3. Collect one JSON return line per dispatched ID. Validate each against the return shape (`AGENTS.md` § Subagent
   handoffs).
   - **No return, or an invalid line:** retry that ID once. A second failure is recorded as
     `{"status": "failed", "root_id": "<id>", "reason": "no return"}` (or the invalid output, quoted).
   - **Same zd# from two IDs:** re-run those IDs one after another, so the second sees the first's file.
4. **Workers unavailable** (no Agent tool, or the `hub-thread-harvester` agent type is missing): read
   `agents/thread-harvester.md` and apply it inline, one thread at a time; state
   `hub-thread-harvester fallback: inline (<reason>)` once in the Phase 3 report.

## Phase 3 - Index and report

**Ticket and link mode.** Print the written path and a one-line summary from the `row` line (zd#, subject, status,
last-activity, and the change label - `new`, `unchanged since <prev_last_activity>`, or `updated since
<prev_last_activity>`). Print any other status with its `reason` instead. On `row`, suggest
`` `/investigate <zd#>` ``.

**Assignee mode.** Write a harvest index at `tickets/hub-harvest/<emaillocalpart>-<YYYY-MM-DD>.md` from the `row`
lines, rows grouped by status (Open, Pending, Solved, Closed), then print the same content.

```
# Hub harvest - <assignee email> - <today>

Window: <since> to <until> (anchor: last activity). Channel: Zendesk Notifications. Threads: <N>.

- Dropped: <root_id> (#<zd#>) - <reason>
- Skipped: <root_id> (#<zd#>) - <reason>
- Failed: <root_id> - <reason>
- Not a Zendesk thread: <root_id> - <reason>

Change: <N> new, <M> updated, <K> unchanged. Matched via: <N> assignee, <M> reply, unassigned.

## <Status>

| zd# | Subject | Customer | Last activity | analysis? | Change | Matched via | Thread |
|---|---|---|---|---|---|---|---|
| <zd#> | <subject> | <customer> | <last-activity> | yes/no | new/updated/unchanged | assignee/reply, unassigned | tickets/<zd#>/zendesk-thread.md |
```

- **Note bullets:** one per non-`row` return, all before the first `## <Status>` heading, so the status sections
  stay the only `##` blocks; omit a bullet type with no entries. The run is never silently partial.
- **Table cells:** escape `|` in a subject or customer as `\|`.
