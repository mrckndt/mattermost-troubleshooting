---
name: sev-escalation
description: Draft (and, after review, send via Gmail) a Sev1/Sev2 escalation-workflow email - a mandatory workflow stage or an optional status update. Args: ticket ID [stage].
user-invocable: true
---

Args: $ARGUMENTS

Draft a Sev1/Sev2 escalation-workflow email per `AGENTS.md`'s Sev1/Sev2 escalation workflow contract, and -
only after explicit engineer review - send it via Gmail.

If `mcp__claude_ai_Gmail__*` tools aren't available, say so per `AGENTS.md`'s Skip convention and stop before
Phase 4 - there's no fallback send path.

## How to reason

1. Parse `$ARGUMENTS`: first token is the ticket reference, second (optional) token is the stage
   (`initial | workaround | resolution | postmortem | status-update`).
2. Follow the phases below in order. Never call `send_message` before Phase 7's explicit confirmation.

## Phase 0 - Resolve ticket

Same resolution order as `/kb-article` Phase 0, ticket mode only - an escalation email always needs a
Zendesk reference and org, so there is no no-ticket mode:

1. `$ARGUMENTS`'s first token is a bare ticket number (`^[0-9]+$`) and `tickets/<that number>/` exists: use it directly.
2. Otherwise apply `/resolve-ticket-id`'s normalization rules inline, not as a nested skill call.
3. Otherwise, if this conversation is already working a specific ticket: use that `<ID>`.
4. Otherwise: ask.

## Phase 1 - Confirm severity

- If `tickets/<ID>/gmail-escalation-thread.md` exists, use its `Severity` header value; state it, don't
  re-ask unless the engineer flags a change.
- Otherwise, if `tickets/<ID>/analysis.md` has a `Severity` field, offer it as a starting point - state its
  `Inferred`/`Customer-stated` tag - still ask the engineer to confirm or override, never use it silently.
- Otherwise, ask/confirm Sev1 or Sev2 against `AGENTS.md`'s Defect and incident severity scale (cite it so
  the engineer can self-check). If the engineer states Sev3/Sev4: say this workflow doesn't apply, stop.
- Once confirmed, patch `analysis.md`'s `Severity` field to `<value> (Confirmed by engineer)`, superseding
  the prior value in place per `AGENTS.md`'s Current-state convention.

## Phase 2 - Determine stage

- `$ARGUMENTS` names a stage: use it.
- Else, no `tickets/<ID>/gmail-escalation-thread.md` yet: `initial`.
- Else: read its `Last stage sent`, suggest the next stage below, ask the engineer to confirm or override.

| Last stage sent | Suggested next |
|---|---|
| (none) | Initial Notification |
| Initial Notification | Workaround Guidance |
| Workaround Guidance | Resolution & De-escalation |
| Resolution & De-escalation | Postmortem Information |
| Postmortem Information | workflow complete - ask what they want |

Interim Status Update is never suggested; only used when the engineer explicitly names it.

## Phase 3 - Gather content

Always re-read from disk, never trust session memory.

**Identity fields** (`Customer`, `Organization`, `Zendesk`, `Support level`): `zendesk-thread.md`'s header
first. If that file is missing or a field is blank there, check `analysis.md`'s `Deployment`/`Correlation`
prose for a mention (it's often derived from the same conversation). Still missing: ask the engineer to
hand-fill it - never guess. `Customer` is the human-readable name; `Zendesk Organization` is the org record
URL, `"unknown"` when not present - keep them as two separate fields in the email (see the template below),
don't collapse one into the other.

**Narrative fields** (Description, Current Status, Resolution): `analysis.md`'s `Reported symptom`,
`Correlation`, `Current hypothesis`, `Resolution` first. If `analysis.md` doesn't exist, fall back to
`zendesk-thread.md`'s raw conversation; still missing, ask the engineer instead of guessing.

| Stage | Content rules |
|---|---|
| Initial Notification | Description from `Reported symptom` + `Correlation`/`Current hypothesis`. `Next Update` is the engineer's free text - no built-in SLA/timing logic. |
| Workaround Guidance | KB-article check plus workaround wording rules - see below. |
| Resolution & De-escalation | Source from `analysis.md`'s `Resolution` field; confirm/edit with the engineer. |
| Postmortem Information | Ask the engineer for the postmortem doc link or attachment - not derivable from ticket data. |
| Interim Status Update (optional) | Draft from `analysis.md`'s latest `Steps and outcomes`/`Open questions`/`Next steps`; confirm before drafting. |

**Workaround Guidance details:**
- Check `tickets/<ID>/kb-article.md` exists. If not, remind the engineer (the workflow requires it) and ask:
  run `/kb-article` now, supply an existing KB link, or proceed without one.
- If it exists, a local file isn't itself a customer-facing link - ask whether it's been published and
  shared with the customer yet. If yes, ask for that URL. If not, offer all three explicitly: hold this
  email until it's published, proceed with a placeholder to fill in later, or proceed without any KB
  reference this round (a legitimate edge case, e.g. urgency outweighs having the link ready) - don't rely
  on the engineer overriding your question to say this themselves.
- **Never write a bare domain (e.g. `support.mattermost.com`) as prose when there's no real URL to attach.**
  Gmail auto-linkifies domain-shaped text on display, which would make an unpublished reference look like a
  working link. Say "not yet published" with no destination named instead.
- Suggest workaround wording only when `analysis.md`/`zendesk-thread.md` shows an explicit customer
  confirmation it worked, labeled "inferred - confirm". Otherwise ask the engineer to state it - offering
  an existing KB article's wording as a starting point to confirm/edit is fine, that's still asking.
- Always show and confirm before drafting, either way.

## Phase 4 - Render

- `To: func-sev1sev2-escalation@mattermost.com`, `Cc: dept-customer-support@mattermost.com`.
- Subject, Initial Notification only: `<Severity> #Radar - <short description> (<Customer, name only, no
  parenthetical>)`. Later stages inherit `Re:` via Gmail threading - no new subject needed.
- Render both `body` (plain text, flat `Label: value` lines, no Markdown) and `htmlBody` (same content,
  field labels wrapped in `<b>...</b>`) - `body` becomes the plain-text alternative when both are given.
- Include the customer/org name, Zendesk ID, and version - required by the workflow, not a Boundaries
  violation (see `AGENTS.md` Boundaries).

<initial_notification_template>
Severity: <Sev1 | Sev2>

Date/Time: <date, time UTC>

Zendesk Reference ID: #<n>

Customer: <human-readable name, per the identity-fields precedence above>

Organization: <Zendesk Organization URL - omit this line entirely if "unknown">

Description: <what happened, root cause hypothesis so far, customer's env/version/tier, what they're asking for>

Current Status: <what support is waiting on>

Next Update: <engineer's free text>

Best Regards,
<engineer name>
<title>, Mattermost, Inc.
<engineer email> | mattermost.com
</initial_notification_template>

Workaround Guidance / Resolution & De-escalation / Postmortem Information / Interim Status Update: reply
body, no repeated header fields (severity/org/Zendesk ID already established in the thread) -

| Stage | Body sections |
|---|---|
| Workaround Guidance | Workaround description, KB article link, Current Status, Next Update |
| Resolution & De-escalation | Summary, Current Status (resolved bullets), Next Steps & Mitigations, explicit Escalation Closure statement |
| Postmortem Information | Short note plus the postmortem doc link or attachment |
| Interim Status Update | Current Status, Risks (optional), Next Steps |

All replies close with the same sign-off block as the template above.

## Phase 5 - Resolve Gmail thread

- Initial Notification: no thread yet, skip.
- Otherwise: read the Gmail thread ID from `tickets/<ID>/gmail-escalation-thread.md`, call `get_thread` for
  the latest message ID (`replyToMessageId`).
- **Fallback**, file missing on a non-initial stage: assume it was lost, not that no thread exists. Call
  `search_threads` (Zendesk reference and/or customer org in the subject, scoped to the escalation alias).
  - Exactly one match: use its thread ID, offer to recreate `gmail-escalation-thread.md` from it.
  - Zero or multiple matches: show what was found, ask the engineer how to proceed. Never guess.

## Phase 6 - Create draft

Print the email for review first, rendered readably (bold labels, clickable links), not the raw HTML body -
then call `mcp__claude_ai_Gmail__create_draft` (`replyToMessageId` set for replies). This order matters: the
tool-call permission prompt shows the raw HTML regardless, so the readable version needs to be seen first,
not buried after it.

## Phase 7 - Confirm and send

Ask: send now / edit content / leave as draft only.
- Send: call `mcp__claude_ai_Gmail__send_message` with that `draftId`.
- Edit: loop back to the relevant Phase 3/4 content, re-render, re-ask.
- Leave as draft: stop; report the draft ID.

Never call `send_message` without this explicit per-run confirmation.

## Phase 8 - Update gmail-escalation-thread.md

- No existing file (Initial Notification only): write it fresh - header plus the first `## Stages sent`
  entry.
- Existing file (any later stage): patch only the `Last stage sent` header line in place, then append one
  new numbered `## Stages sent` entry, continuing the numbering. Never rewrite or renumber existing entries -
  `Gmail thread ID` and `Opened` don't change after Initial Notification, leave them as already written.
- **Each entry is verbatim.** Copy the sent subject and body character-for-character: no summarizing,
  paraphrasing, or reformatting. This is the local record of what was actually communicated to the
  escalation chain - a paraphrase would make it unreliable for exactly the review it exists for.

<gmail_escalation_thread_template>
- Severity: <Sev1 | Sev2>
- Gmail thread ID: <id>
- Zendesk reference: #<n>
- Escalation alias: func-sev1sev2-escalation@mattermost.com
- Opened: <date>
- Last stage sent: <stage> - <date>

## Stages sent

### 1. Initial Notification - <date/time> (message <id>)
Subject: <verbatim subject>

<verbatim body as sent>
</gmail_escalation_thread_template>
