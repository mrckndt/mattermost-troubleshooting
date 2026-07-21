---
name: hub-harvest
description: Fetch a Zendesk ticket thread (or all of a TSE's assigned threads in a time window) from the Mattermost Hub notifications channel into tickets/<zd#>/hub-thread.md. Ready for /investigate.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Fetch Zendesk ticket conversations from the Mattermost Hub and persist each one to disk once,
so later work (`/investigate`) reads from `tickets/<zd#>/` instead of re-querying
the Hub.

- **Source:** fixed Hub channel `p77n3165i3r89kugxyabx9wwer` ("Zendesk Notifications", team Staff).
- **Thread shape:** one thread per ticket - a root `New Ticket: <subject> (#zdNNNNN)` post plus threaded replies.
  The root post's own ID is the thread `Root ID`.
- **Zendesk-mirrored replies:** `New Reply (Customer)`, `New Reply (Mattermost)`, `New Internal Note` - authored
  by `zendesk_bot`, each carrying a `Current Status` and `Current Assignee` snapshot.
- **Non-mirrored messages:** a thread can also contain plain Mattermost messages with no Zendesk metadata (e.g. a
  TSE invoking `@techsupport` inline, or the bot's resulting drafted reply) - Phase 2 labels these internal
  workspace activity and excludes them from status/assignee derivation.

## Phase 0 - Setup and mode

1. Confirm the Mattermost Hub MCP is present (`mcp__claude_ai_Mattermost_Hub__*`). If absent,
   state `Mattermost Hub search skipped: MCP not available` and stop. Never block.
2. If `$ARGUMENTS` is empty, ask for a ticket number or an assignee email before proceeding.
3. Pick the mode: an `@` token means **assignee mode** (that token is the email, the remainder
   is the time range); otherwise **ticket mode**: run `/resolve-ticket-id <the non-@ remainder>` inline to get the ticket number.

## Phase 1 - Locate roots

Use `mcp__claude_ai_Mattermost_Hub__search_posts` with `channel_id` set to
`p77n3165i3r89kugxyabx9wwer`. Keep `keyword_limit`/`semantic_limit` at their defaults; raising
them risks an oversized result truncated to a file.

**Ticket mode.** Query the ticket number (bare and `zd<num>` forms). The `New Ticket: ... (#<num>)`
post's `Post ID` is the `Root ID`. If none matches, state `no New Ticket post found for #<num>`
and stop.

**Assignee mode.**
1. Resolve `[since, until]` from the remainder of `$ARGUMENTS`: an explicit
   `YYYY-MM-DD..YYYY-MM-DD` range, a natural-language phrase (`last 2 weeks`, `June`), or, absent
   any time expression, a 30-day lookback ending today. Echo the resolved window before fetching.
2. Resolve the assignee's display name via `mcp__claude_ai_Mattermost_Hub__search_users`, querying the email's
   local part (before `@`) - the full email address does not match. Success: use the returned name. Failure or
   empty result: fall back to title-casing the local part (`firstname.lastname` -> `Firstname Lastname`).
   Discovery/signature-matching aid only, never ground truth by itself - Phase 2 still decides.
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
   not be a thread's newest post; the real filter is Phase 2, against a full-thread fetch.

## Phase 2 - Fetch and persist

For each `Root ID`, call `mcp__claude_ai_Mattermost_Hub__read_post` with `include_thread=true`.
If a thread is too large and the result is truncated to a file, read it via a subagent
(instruct it to return the extracted fields below, `body` copied verbatim per the rule below), or
state `Mattermost Hub result skipped: <zd#> oversized` and continue.

Only `New Reply (...)`/`New Internal Note` posts carry `Current Status`/`Current Assignee`; the
root `New Ticket` post and any internal workspace activity (defined above) do not - skip them when
deriving status/assignee, but still include them in the written conversation, labeled `Internal
workspace activity (<author username>)`, body from `Message` instead of `Description`.

From each thread, derive:
- **zd#** and **subject** - from the root `New Ticket: <subject> (#<num>)` (zd# names the
  `tickets/` directory).
- **requester**, **priority**, **support level**, **tags**, **references** - from the root
  attachment (trim trailing whitespace and stray `\n`).
- **zendesk**, **zendesk_org**, **salesforce** - parse `references` as a pipe-delimited list of
  labeled Markdown links (`[Zendesk Ticket](...) | [Zendesk Organization](...) | [Salesforce
  Account](...)`) and extract each URL by its label. Default any label not present to `"unknown"`
  - don't assume all three always appear.
- **customer** - the organization from References/attachment, else the requester's email domain
  plus any Account Manager.
- **status (latest)** / **assignee (latest)** - the verbatim value from the single newest post
  that carries the field. An empty `Current Assignee` on that post means unassigned now - do not
  scan backward for an older non-empty value.
- **created** / **last-activity** - root post time / newest post time (any post type).
- **messages** - every post in order: Post ID, index, direction (Customer / Mattermost / Internal
  note / New ticket / Internal workspace activity), timestamp, visible assignee for Mattermost
  replies, body, and any links or file references.
- **Body is verbatim.** Copy `Description`/`Message` character-for-character: no summarizing,
  paraphrasing, tone-fixing, typo-fixing, or reformatting. These are untrusted customer/engineer
  quotes (see `AGENTS.md` boundaries) - transcribe them, don't edit them.

**Assignee mode filter.** Keep a thread, subject to its last-activity falling within
`[since, until]` in both cases, if EITHER:
- **(a) assignee match** - its derived latest assignee equals the `$ARGUMENTS` email. Wins outright whenever the
  latest assignee is non-empty, regardless of who authored intervening replies (only the latest snapshot governs).
- **(b) unassigned-reply match** - at least one `Reply (Mattermost)` post has an empty `Current Assignee` value
  *on that post itself* (its own snapshot, not the thread's latest) AND is signed with the display name resolved
  in Phase 1. Matches even if a different, later person is the final assignee - it only asks whether this person
  replied during an unassigned gap, independent of what happened afterward.

Drop the rest (note the count dropped). Record which rule matched, `assignee` or
`reply, unassigned`, and carry it into Phase 3 alongside the change label - (b) is a weaker
signal than a formal assignment and should stay visibly distinguishable from (a).

**Change classification.** Before writing, label each kept thread `new` / `updated` / `unchanged`,
purely as a reporting signal for downstream consumers; it does not change what this skill writes:
- No existing `tickets/<zd#>/hub-thread.md` -> `new`.
- Existing file whose `- Last activity:` header line parses and equals the last-activity value
  just derived -> `unchanged`.
- Existing file whose parsed `Last activity` differs, or whose line is missing/unparseable ->
  `updated`.

Carry the label into Phase 3. This applies the same way in ticket mode and assignee mode; both
persist here, per Root ID.

Persist `tickets/<zd#>/hub-thread.md` per kept thread, per label. Posts are immutable once
mirrored, so only patch what's new:
- **new** - no existing file; write it in full with the template below.
- **unchanged** - patch only `- Harvested: <today>` in place.
- **updated** - patch the header block (`# Ticket ...` through the blank line before
  `## Conversation`) with fresh values, then append one `### <next index>. ...` block per fetched
  post not already present (matched by its `(post <id>)` marker), continuing numbering in fetch
  order. Never rewrite or renumber existing blocks.
- **Migration fallback** - any `### N.` heading missing `(post <id>)`, or an unparseable header,
  triggers a one-time full overwrite; it self-migrates from there.

Reuse-safe: only ever writes `hub-thread.md`, never another file in the ticket dir. Record whether
`analysis.md`/`analysis-full.md` exists there.

Template (apply the `AGENTS.md` formatting constraints - no em dashes, plain ``` fences):

```
# Ticket <zd#> - <subject>

- Source: Mattermost Hub, Zendesk Notifications channel, root post <Root ID>
- Zendesk: <Zendesk Ticket URL from References, or "unknown">
- Zendesk Organization: <Zendesk Organization URL from References, or "unknown">
- Salesforce: <Salesforce Account URL from References, or "unknown">
- Customer: <org / requester domain>
- Requester: <requester>
- Priority: <priority>
- Support level: <support level>
- Status (latest): <status>
- Assignee (latest): <assignee email, or "unassigned">
- Created: <root time>
- Last activity: <last post time>
- Tags: <tags>
- Harvested: <today> by /hub-harvest

## Conversation

### 1. New ticket (customer) - <root time> (post <Root ID>)

<root Description>

Links/attachments: <any URLs or file references, or "none">

### 2. Reply (Mattermost, <assignee>) - <time> (post <Post ID>)

<Description>

<... one ### block per post, in order, each tagged (post <Post ID>); label per the direction list above ...>
```

## Phase 3 - Index and report

**Ticket mode.** Print the written path and a one-line summary (zd#, subject, status,
last-activity, and the change label - `new`, `unchanged since <date>`, or `updated since <date>`,
where `<date>` is the last-activity value the existing file recorded before this fetch). Suggest
`` `/investigate <zd#>` ``.

**Assignee mode.** Write a harvest index at `tickets/hub-harvest/<emaillocalpart>-<YYYY-MM-DD>.md`,
rows grouped by status (Open, Pending, Solved, Closed), then print the same table.

```
# Hub harvest - <assignee email> - <today>

Window: <since> to <until> (anchor: last activity). Channel: Zendesk Notifications. Threads: <N>.

## <Status>

| zd# | Subject | Customer | Last activity | analysis? | Change | Matched via | Thread |
|---|---|---|---|---|---|---|---|
| <zd#> | <subject> | <customer> | <last-activity> | yes/no | new/updated/unchanged | assignee/reply, unassigned | tickets/<zd#>/hub-thread.md |
```

Note any threads dropped by the window/assignee filter and any skipped as oversized, so the run
is not silently partial. Add rollup lines after those notes: `Change: <N> new, <M> updated, <K>
unchanged.` and `Matched via: <N> assignee, <M> reply, unassigned.`
