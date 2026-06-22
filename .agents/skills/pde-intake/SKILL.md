---
name: pde-intake
description: Generate a structured PD&E intake post (feature request, bug report, or security issue) from the current troubleshooting context. Optional arg: issue title or short description.
user-invocable: true
---

Args: $ARGUMENTS

Activate when the user asks to file a feature request, bug report, or security issue for PD&E.

## How to reason

1. Review everything known: `./tickets/<name>/` files, the conversation, logs, config, the customer's ask, and why current behavior is insufficient.
2. If $ARGUMENTS is provided, treat it as the issue title or description and incorporate it.
3. Follow the phases below in order.

## Inputs

Required (ask once, batched, if any are missing):
- Issue type: Feature Request / Bug Report / Security Issue / Other.
- Customer / organization name.
- At least one source URL: Zendesk ticket OR Hub link. Use both if known; if neither, ask before proceeding.
- Feature title (imperative).
- Problem today + desired behavior.
- Affected persona.
- How often it comes up.
- Deployment type: Cloud / On-premises / Air-gapped.
- Product tier: Professional / Enterprise / Enterprise Advanced.
- Urgency / Severity: deal/renewal tie-in, bug severity, or none.

Optional (never ask; use if known): contact full name + title + email; Jira URL/key; scope of change (UI / API / admin policy / other); related links.

## Output

Print raw Markdown, not in a code block. Follow the template exactly.
- Render every URL as a Markdown link; never append the bare URL. Labels: Zendesk `#<ID>` (e.g. `#48217`), Jira key (e.g. `MM-12345`), other: 1-3 word descriptor.
- Never invent or guess a URL, key, or email. Per-field rules for unknowns:
  - **Contact:** omit the line if name unknown. Drop `, Title` or `, email` if unknown. Render email as plain text.
  - **Jira Ticket:** omit the line if URL unknown.
  - **Zendesk Ticket** / **Hub Post:** at least one must render; omit the other if unknown.
  - All other fields: write `N/A` if not applicable.

## Template

```
# [Issue Type]: [Customer] - [Short, Descriptive Title]

**Customer:** [Company Name]
**Contact:** [First Surname][, Title][, email]
**Zendesk Ticket:** [#ID](URL)
**Hub Post:** [Label](URL)
**Jira Ticket:** [KEY](URL)
**Deployment:** Cloud / On-premises / Air-gapped
**Tier:** Professional / Enterprise / Enterprise Advanced
**Persona:** [affected role]
**Frequency:** [how often it comes up]
**Scope:** [UI / API / admin policy / other]
**Urgency / Severity:** [deal/renewal tie-in, bug severity, or none]
**Problem:** [current behavior → desired behavior]
```
