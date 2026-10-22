---
name: sev-email
description: Draft (and, after review, send via Gmail) a Sev1/Sev2 escalation-workflow email - one of the four mandatory workflow stages. Args: ticket ID [stage].
user-invocable: true
---

Args: $ARGUMENTS

Draft a Sev1/Sev2 escalation-workflow email per `AGENTS.md`'s Sev1/Sev2 escalation workflow contract, and -
only after explicit engineer review - send it via Gmail.

If `mcp__claude_ai_Gmail__*` tools aren't available, say so per `AGENTS.md`'s Skip convention and stop before
Phase 4 - there's no fallback send path.

## How to reason

1. Parse `$ARGUMENTS`: first token is the ticket reference, second (optional) token is the stage
   (`initial | workaround | resolution | postmortem`).
2. Follow the phases below in order. Never call `send_message` before Phase 7's explicit confirmation.

## Phase 0 - Resolve ticket

Same resolution order as `/kb-article` Phase 0, ticket mode only - an escalation email always needs a
Zendesk reference and org, so there is no no-ticket mode:

1. `$ARGUMENTS`'s first token is a bare ticket number (`^[0-9]+$`) and `tickets/<that number>/` exists: use it directly.
2. Otherwise apply `/resolve-ticket-id`'s normalization rules inline, not as a nested skill call.
3. Otherwise, if this conversation is already working a specific ticket: use that `<ID>`.
4. Otherwise: ask.

## Phase 1 - Confirm severity

- Use `gmail-escalation-thread.md`'s `Severity` header, else the severity part of `analysis.md`'s `Severity` when
  `Confirmed by engineer`; state it, re-ask only if the engineer flags a change.
- Otherwise offer a starting point the engineer confirms or overrides, never used silently: `analysis.md`'s
  `Severity` (state its `Inferred`/`Customer-stated` tag), else `zendesk-thread.md`'s `Priority` mapped per
  `AGENTS.md`, else ask against `AGENTS.md`'s Defect and incident severity scale (cite it so the engineer can
  self-check).
- Sev3/Sev4, confirmed or stated by the engineer: say this workflow doesn't apply, stop.
- Once confirmed, if `tickets/<ID>/analysis.md` exists, patch the severity part of its `Severity` field to
  `<value> (Confirmed by engineer)`, keeping Reach (none recorded: ask for it) and re-reading Priority from
  `AGENTS.md`'s Reach x severity table, superseding the prior value in place per `AGENTS.md`'s Current-state
  sections. No `analysis.md`: skip; Phase 8 records the value.

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

## Phase 3 - Gather content

Always re-read from disk, never trust session memory.

**Identity fields (`Customer`, `Organization` (`Zendesk Organization`), `Zendesk`):** `zendesk-thread.md`'s header
first. If that file is missing or a field is blank there, check `analysis.md`'s `Deployment`/`Correlation`
prose for a mention (it's often derived from the same conversation). Still missing: ask the engineer to
hand-fill it - never guess. `Customer` is the human-readable name; `Zendesk Organization` is the org record
URL, `"unknown"` when not present - keep them as two separate fields in the email (see the template below),
don't collapse one into the other.

**Narrative fields (template in Phase 4):** `analysis.md` first. If it doesn't exist, fall back to
`zendesk-thread.md`'s raw conversation; still missing, ask the engineer instead of guessing.

| Field | Source |
|---|---|
| Summary (1-3 sentences) | `Reported symptom` + `Current hypothesis` |
| Status, Next steps | `Current hypothesis`, `Next steps`, plus the stage content below |
| Declared | Initial Notification: ask the engineer (time the issue was verified as real). Later stages: copy from `gmail-escalation-thread.md`'s first entry; file missing: ask the engineer. |
| Customer impact | `Deployment` (env, version, tier) + `Reported symptom` |
| Workaround | `Workaround`; Workaround Guidance details below; later stages carry forward the `Workaround:` line of the last sent entry in `gmail-escalation-thread.md` when it has one |
| Next update | Engineer's free text - no built-in SLA/timing logic |

Per-stage content the Sev1/Sev2 Support Ticket Workflow requires:

| Stage | Required content (workflow step) |
|---|---|
| Initial Notification | Notification on identifying the incident (step 3). |
| Workaround Guidance | Workaround plus KB article link, confirming it was shared with the customer (step 5). |
| Resolution & De-escalation | Resolution details from `analysis.md`'s `Resolution`; confirm/edit with the engineer (step 8). |
| Postmortem Information | Postmortem process and findings (step 3), with the finalized postmortem document as an attachment (step 10). |

**Postmortem attachment:** `tickets/<ID>/postmortem.md` when it exists, after the engineer confirms it is the
finalized version; list any `[to fill in the post-mortem session]` or `[unknown` placeholders still in it before
asking. No such file: ask the engineer for the file.

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

- `To: func-sev1sev2-escalation@mattermost.com`, `Cc: dept-customer-support@mattermost.com` (Cc is a workspace
  convention).
- One template for every stage: the `Sev1_2 #radar Email Template`, plus the Zendesk identity fields
  appended after the template's own fields. The template's `Subject:`/`Body:` are labels, not email content:
  the subject goes in `subject`, the summary sentences open the body unlabeled.
- Subject is set on Initial Notification; later stages inherit `Re:` via Gmail threading.
- `Workaround:` (from the template's example) is omitted when `analysis.md` has `Available: no`/`unknown` and no
  sent entry carries one; Workaround Guidance always carries it. `Organization:` is omitted when `"unknown"`.
- Render both `body` (plain text, flat `Label: value` lines, no Markdown) and `htmlBody` (same content,
  field labels wrapped in `<b>...</b>`) - `body` becomes the plain-text alternative when both are given.
- No hand-written sign-off; set `includeSignature: true` on `create_draft`.
- Include the customer/org name, Zendesk ID, and version - required by the workflow, not a Boundaries
  violation (see `AGENTS.md` Boundaries).

<radar_template>
Subject: <Sev1 | Sev2> #radar: <short one-line summary> - <Customer, name only>

<1-3 sentences concisely describing the issue>

Severity: <Sev1 | Sev2> - <label and definition from AGENTS.md's severity scale>

Status: <current status>

Declared: <time the issue was verified as real, UTC>

Customer impact: <any known customer impact>

Workaround: <workaround and KB article link>

Next steps: <active next steps>

Next update: <when the next update is expected>

Zendesk Reference ID: #<n>

Customer: <human-readable name, per the identity-fields precedence above>

Organization: <Zendesk Organization URL>
</radar_template>

## Phase 5 - Resolve Gmail thread

- Initial Notification: no thread yet, skip.
- Otherwise: read the Gmail thread ID from `tickets/<ID>/gmail-escalation-thread.md`, call `get_thread` for
  the latest message ID (`replyToMessageId`).
- **Fallback**, file missing on a non-initial stage: assume it was lost, not that no thread exists. Call
  `search_threads` scoped to the escalation alias, matching `Zendesk Reference ID: #<n>` in the body.
  - Exactly one match: use its thread ID, offer to recreate `gmail-escalation-thread.md` from it: header per the
    template in Phase 8 (`Opened` = first message date, `Last stage sent` = the latest stage found), one
    `## Stages sent` entry per message already in the thread, verbatim.
  - Zero or multiple matches: show what was found, ask the engineer how to proceed. Never guess.

## Phase 6 - Create draft

Print the email for review first, rendered readably (bold labels, clickable links), not the raw HTML body -
then call `mcp__claude_ai_Gmail__create_draft` (`replyToMessageId` set for replies; `attachments` carries the
postmortem document on Postmortem Information, base64 `content` with `filename` and `mimeType`). The order
matters: the permission prompt shows only the raw HTML.

## Phase 7 - Confirm and send

Ask: send now / edit content / leave as draft only.
- Send: call `mcp__claude_ai_Gmail__send_message` with that `draftId`.
- Edit: loop back to the relevant Phase 3/4 content, re-render, re-ask.
- Leave as draft: stop; report the draft ID.

Never call `send_message` without this explicit per-run confirmation.

## Phase 8 - Update gmail-escalation-thread.md

- No existing file (Initial Notification, or a later stage whose recreate offer in Phase 5 was declined): write it
  fresh - header plus the first `## Stages sent` entry.
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
