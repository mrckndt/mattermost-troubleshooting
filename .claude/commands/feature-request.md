---
description: Generate a structured feature-request post from the current troubleshooting context. Optional arg: feature description or short title.
argument-hint: [feature description or short title]
---

Args: $ARGUMENTS

Activate when the user asks to file or write up a feature request. Audience: Mattermost PMs.

## How to reason

1. Review everything known: `./tickets/<name>/` files, the conversation, logs, config, the customer's ask, and why current behavior is insufficient.
2. If $ARGUMENTS is provided, treat it as the feature title or description and incorporate it.
3. Follow the two phases below in order.

## Phase 1 - Gather inputs

Required (ask once, batched, if any are missing):
- Customer / organization name.
- At least one source URL: Zendesk ticket OR Hub link. Use both if known; if neither, ask before proceeding.
- Feature title (imperative).
- Problem today + desired behavior.
- Affected persona (e.g. team admins, end users).
- How often it comes up (e.g. single ticket, recurring theme).
- Deployment type: Cloud / On-premises / Air-gapped.
- Product tier: Professional / Enterprise / Enterprise Advanced.
- Urgency context: deal/renewal tie-in, or none.

Optional (never ask; use if known): contact full name + title + email; Jira URL/key; scope of change (UI / API / admin policy / other); related links.

## Phase 2 - Generate Markdown

- Print the Markdown raw (not in a code block). Follow the template exactly; do not add sections. Preserve the two-space line-break suffixes on the header lines.
- Render every URL as a Markdown link; never append the bare URL. Labels: Zendesk `#<ID>` (e.g. `#48217`), Jira key (e.g. `MM-12345`), GitHub `owner/repo#N`, Mattermost thread: short descriptor (e.g. `community thread`), other: 1-3 word descriptor.
- Never invent or guess a URL, key, title, or email. Per-field rules for unknowns:
  - **Contact:** if name is unknown, omit the entire line. Drop `, Title` if title unknown; drop `, email` if email unknown. If email is known, render as plain text (Mattermost auto-links); do not use `<...>` autolink or explicit Markdown link syntax.
  - **Jira Ticket:** if URL unknown, omit the entire line. Never write `N/A`, never invent.
  - **Zendesk Ticket** / **Hub Post:** at least one must render; if only one is known, omit the other line entirely (no `N/A`).
  - **References:** drop any bullet whose link is unknown; if both unknown, write the section as `N/A`.
- For any other section with no applicable content, write `N/A` rather than omitting it.

## Writing style

- Audience: PM owning the affected product area. Product literacy, no ticket context.
- Lead with the ask; a PM should grasp it in the first two sentences.
- Be specific about scope: what it does, what it does not do, where it fits (config, UI, API, plugin).
- Frame in product terms (impact, frequency, persona). Surface PM signals: how many users/customers, blocker vs friction, revenue tied to it.
- No vague language, no implementation proposals unless the customer asked. No preamble or trailing text.

## Template

```
# Feature Request: [Customer] - [Short, Descriptive Title]

**Customer:** [Company Name]  
**Contact:** [First Surname][, Title if known][, email if known]  
**Zendesk Ticket:** [#ID](URL)  
**Hub Post:** [Label](URL)  
**Jira Ticket:** [KEY](URL)  
**Deployment:** Cloud / On-premises / Air-gapped  
**Tier:** Professional / Enterprise / Enterprise Advanced  

## Summary
_One to two sentences: the ask and why it matters._

## Problem
_Current behavior, desired behavior, affected persona, how often it comes up, scope (UI / API / admin policy), urgency or deal context._

## References
- [Label](URL)
```
