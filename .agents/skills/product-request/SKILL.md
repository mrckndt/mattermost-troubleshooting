---
name: product-request
description: Generate a structured PD&E intake post (feature request, bug report, or security issue) from the current troubleshooting context, optionally sent as a Hub DM to the PDE Intake Agent after review. Optional arg: issue title or short description.
user-invocable: true
---

Args: $ARGUMENTS

Activate when the user asks to file a feature request, bug report, or security issue for PD&E.

## How to reason

1. Review everything known: `./tickets/<name>/` files, the conversation, logs, config, the customer's ask, and why current behavior is insufficient.
2. If $ARGUMENTS is provided, treat it as the issue title or description and incorporate it.
3. Follow the phases below in order. Call `mcp__claude_ai_Mattermost_Hub__dm` only after the send confirmation in
   "Send to PDE Intake Agent".

## Inputs

Fill the template best effort from `./tickets/<name>/` (`zendesk-thread.md`, `analysis.md`), the conversation and
$ARGUMENTS. Write `Unknown` for any field not established; the intake accepts gaps, so ask only for:
- **Request type** (bug / design / security / feature), only when it can't be inferred.
- **Source link:** a Zendesk ticket or Hub link, only when neither is known.

Field sources, when present:
- **Mattermost version, deployment type, tier, scale:** `analysis.md` `Deployment`.
- **Actual, expected, steps to reproduce, impact:** `analysis.md` `Reported symptom`.
- **Workaround available?:** `analysis.md` `Workaround`.
- **Logs / error messages:** a short snippet from `Evidence collected` or the ticket files.
- **Urgency / deadline:** for bugs, the Sev level per AGENTS.md's Defect and incident severity scale, plus any
  renewal, escalation or deadline signal; for other types, the renewal/deal/deadline signal only.
- **Affected customer(s), contact, Salesforce Account URL:** `zendesk-thread.md` header.
- **ARR, seats, potential ARR:** only when stated in the ticket files or conversation.
- **Jira key:** `analysis.md` `Tracking` or the conversation.

A customer-facing Sev1/Sev2 incident also needs `/sev-email` (notifies the internal escalation chain
via email).

## Output

Print raw Markdown, not in a code block. Follow the template exactly.
- Render the common fields, then only the details section matching the request type. Bugs also get the
  `Instructions for PDE Intake Agent` section.
- Render every URL as a Markdown link. Labels: Zendesk `#<ID>` (e.g. `#48217`), Jira key (e.g. `MM-12345`), other:
  1-3 word descriptor. Exception: the Zendesk URL in `Instructions for PDE Intake Agent` stays bare (a Jira field value).
- **Evidence:** list the Zendesk, Hub, Jira and Salesforce links first, then related tickets, docs, customer quotes.
- **Contact:** name, title, email (plain text) as known; under `Customer technical contact` for bugs, appended to
  `Affected customer(s)` otherwise.
- Citing a code-level root cause (e.g. from `analysis.md`): use `function:file`, not a raw line number - line numbers drift and outlive this report's accuracy.
- Never invent or guess a URL, key, email, ARR or seat count; write `Unknown` instead.

## Template

```
### [Request type]: [Customer] - [Title]

**Request type:** [Bug / Design / Security / Feature]
**Title:** [short summary, under 10 words]
**Problem or request:** [what is happening or needed, and why it matters]
**Affected customer(s):** [customer][; contact]
**Users / seats affected:** [count]
**ARR (approx.):** [amount]
**Product tier:** [Professional / Enterprise / Enterprise Advanced / Unknown]
**Deployment type:** [cloud / on-prem / air-gapped / BYOC]
**Urgency / deadline:** [SevN - Label for bugs; renewal risk, escalation, hard date, deal at risk]
**Evidence:** [#ID](URL), [Hub post](URL), [KEY](URL), [Account](URL), [other links, quotes]
**Recurrence:** [one-off, or seen across multiple accounts]

#### Bug details

**Affected area:** [messaging, notifications, admin console, mobile, channels, etc.]
**What the user was trying to do:** [goal]
**Actual behavior:** [actual]
**Expected behavior:** [expected]
**Steps to reproduce:**
1. [step]
2. [step]
3. [step]
**Frequency:** [every time / intermittent]
**Workaround available?:** [yes (describe) / no]
**Mattermost version:** [vX.Y.Z]
**Logs / error messages:** [short snippet]
**Screenshot or link:** [Label](URL)
**Customer technical contact:** [name, role, email]
**Renewal risk / escalation / deadline:** [details]

#### Feature request details

**Specific capability requested:** [what the customer wants to do that they can't today]
**Current gap, from the customer's point of view:** [what happens today, and the operational consequence]
**Who is affected and how badly:** [customers, user count, what they can't do]
**Customer size:** [headcount or ARR band]
**Operationally critical or convenience?:** [critical / convenience]
**Potential ARR:** [if prospect or expansion]
**Feasibility input:** [anything an SE, TAM, engineer or customer admin has said]

#### Design request details

**Current friction:** [friction]
**Who is affected:** [roles, users]
**What should improve:** [improvement]
**Screenshot or link:** [Label](URL)

#### Security details

**Vulnerability description:** [description]
**Affected area / version:** [area, version]
**Reproduction steps:** [steps, if available]
**Exposure / impact:** [impact]
**Confidentiality concerns:** [concerns]

#### Instructions for PDE Intake Agent

For every Jira ticket created from this request: add the label `customer-bug` and set the Zendesk URL field to
[bare Zendesk URL].
```

In `Instructions for PDE Intake Agent`, drop the `and set the Zendesk URL field to ...` clause when no Zendesk URL is
known.

## Send to PDE Intake Agent

**Recipient:** PDE Intake Agent, user ID `qmz3p1opofyeuq8u8y1zfes9by` (stable anchor), username `@pde-intake`
(what `dm` takes).

1. If `mcp__claude_ai_Mattermost_Hub__*` tools are absent: state `Mattermost Hub send skipped: <reason>` per
   AGENTS.md's Skip convention and stop; the printed post stays available for manual paste.
2. Ask the engineer (AskUserQuestion): **Send as DM to PDE Intake Agent (`@pde-intake`)** / **Don't send**.
   If they request edits instead, apply them, reprint the post, and ask again.
3. On send: call `mcp__claude_ai_Mattermost_Hub__list_agents`, find the entry with ID `qmz3p1opofyeuq8u8y1zfes9by`,
   and use its current username. If that ID isn't listed, stop and tell the engineer; match on the ID only, never on
   name.
4. Call `mcp__claude_ai_Mattermost_Hub__dm` with that `username` and `message` set to the exact Markdown printed
   above, unreworded. Report the returned message ID; the bot replies in that DM on Hub.

Confirmation is per run: ask again every time, even if the engineer sent a previous post in this session.

## Track the Jira ticket

When this run learns the request's Jira key (an input, or the one PD&E created, from the engineer) and
`./tickets/<name>/analysis.md` exists, append it to `Tracking` per `AGENTS.md`'s `analysis.md` schema (format,
skip and `none` rules), URL `https://mattermost.atlassian.net/browse/<key>`, date recorded today. No heading: add
it before `## Session log`. Print the appended line.
