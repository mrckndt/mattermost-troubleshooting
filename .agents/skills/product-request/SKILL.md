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

Required (ask once, batched, if any are missing):
- Issue type: Feature Request / Bug Report / Security Issue / Other.
- Customer / organization name.
- At least one source URL: Zendesk ticket OR Hub link. Use both if known; if neither, ask before proceeding.
- Feature title (imperative).
- Problem today + desired behavior.
- Affected role.
- How often it comes up.
- Deployment type: Cloud / On-premises / Air-gapped.
- Product tier: Professional / Enterprise / Enterprise Advanced.
- Urgency / Severity: for bugs, classify per AGENTS.md's Defect and incident severity scale (Sev1-Sev4); for feature requests, deal/renewal tie-in or none.

A customer-facing Sev1/Sev2 incident also needs `/sev-escalation` (notifies the internal escalation chain
via email).

Optional (never ask; use if known): contact full name + title + email; Jira URL/key; scope of change (UI / API / admin policy / other); related links; Salesforce Account URL (zendesk-thread.md).

## Output

Print raw Markdown, not in a code block. Follow the template exactly.
- Render every URL as a Markdown link; never append the bare URL. Labels: Zendesk `#<ID>` (e.g. `#48217`), Jira key (e.g. `MM-12345`), other: 1-3 word descriptor.
- Citing a code-level root cause (e.g. from `analysis.md`): use `function:file`, not a raw line number - line numbers drift and outlive this report's accuracy.
- Never invent or guess a URL, key, or email. Per-field rules for unknowns:
  - **Contact:** omit the line if name unknown. Drop `, Title` or `, email` if unknown. Render email as plain text.
  - **Jira Ticket:** omit the line if URL unknown.
  - **Salesforce Account:** omit the line if URL unknown.
  - **Zendesk Ticket** / **Hub Post:** at least one must render; omit the other if unknown.
  - All other fields: write `N/A` if not applicable.

## Template

```
### [Issue Type]: [Customer] - [Short, Descriptive Title]

**Customer:** [Company Name]
**Contact:** [First Surname][, Title][, email]
**Salesforce Account:** [Account](URL)
**Zendesk Ticket:** [#ID](URL)
**Hub Post:** [Label](URL)
**Jira Ticket:** [KEY](URL)
**Deployment:** Cloud / On-premises / Air-gapped
**Tier:** Professional / Enterprise / Enterprise Advanced
**Affected Role:** [affected role]
**Frequency:** [how often it comes up]
**Scope:** [UI / API / admin policy / other]
**Urgency / Severity:** [Sev1 - Critical / Sev2 - Serious / Sev3 - Moderate / Sev4 - Minor for bugs; deal/renewal tie-in or none for feature requests]
**Problem:** [current behavior → desired behavior]
```

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
