---
description: Generate a structured feature-request post from the current troubleshooting context. Optional arg: feature description or short title.
argument-hint: [feature description or short title]
---

Args: $ARGUMENTS

Generate a structured feature-request post for the current troubleshooting context, written for Mattermost product managers. Give a PM enough signal to triage without chasing context.

## How to reason

1. Review everything known: `./tickets/<name>/` files, the conversation, logs, config, the customer's ask, and why current behavior is insufficient.
2. If $ARGUMENTS is provided, treat it as the feature title or description and incorporate it.
3. Follow the two phases below in order.

## Feature-request format rules (apply these exactly)

**Phase 1 - Gather inputs**
- Check whether the following are known from the conversation. Required fields: if missing, ask once before proceeding (combine all missing items into a single follow-up). Optional fields: never ask; just use them if known.
  - Customer / organization name (required)
  - Contact full name of the person filing the request - first name and surname together, e.g. "Jane Doe" (optional)
  - Contact title (optional)
  - Contact email address (optional)
  - At least one of the following two is required; use both if both are known:
    - Zendesk ticket URL or ID
    - Mattermost Hub link to the customer chat / channel / thread where the request was raised
  - Jira ticket URL or key, if one already tracks this feature request (optional)
  - Salesforce account / opportunity URL (optional)
  - Concise feature title (required; imperative, what the feature does)
  - Problem / pain point the customer is hitting today, plus the desired behavior they want instead (required)
  - Who is affected: persona such as team admins, end users, enterprise customers (required)
  - How often this comes up: number of customers, recurring theme, single ticket, etc. (required)
  - Customer-stated priority (required; if the customer did not state one, infer the closest fit from their language - do not ask)
  - Related Mattermost thread or related issue links (optional)

**Phase 2 - Generate Markdown**
- Produce the post in Markdown, following the template structure exactly. Do not add sections.
- Print the Markdown as raw text (not inside a code block) so it renders natively in Mattermost.
- Preserve the two-space line-break suffixes on the header lines exactly as shown.
- Render every URL as a clickable Markdown link with a short, meaningful label, e.g. `[#48217](https://mattermost.zendesk.com/agent/tickets/48217)`. Do not append the bare URL afterward. Label conventions:
  - Zendesk ticket: `#<numeric ID>` (e.g. `#48217`).
  - Jira ticket: the issue key (e.g. `MM-12345`).
  - Salesforce account / opportunity: use the company name (same value as the **Customer:** field).
  - GitHub / GitLab issue or PR: `owner/repo#<number>` (e.g. `mattermost/mattermost#1234`).
  - Mattermost post / thread: a short descriptor like `community thread` or `support channel post`.
  - Anything else: a 1-3 word descriptor of what the link points to.
- Per-field presence rules:
  - **Contact:** if the name is unknown, omit the entire `**Contact:**` line. Drop the `, Title` suffix if the title is unknown; drop the `, email` suffix if the email is unknown. Never invent a title or email. If the email is known, render it as plain text (e.g. `jane.doe@example.com`) - Mattermost auto-links emails on its own. Do not wrap in `<...>` autolink syntax (it renders as `addr : mailto:addr`) and do not use explicit Markdown link syntax.
  - **Zendesk Ticket** / **Hub Post:** at least one of these two lines must render. If only one URL is known, omit the line for the other entirely (do not write `N/A`, do not invent a URL). If neither is known, this is a required-field gap - do not generate the post; ask for one of the two.
  - **Jira Ticket:** if no URL is known, omit the entire `**Jira Ticket:**` line; never write `N/A`, never invent a URL or key.
  - **Salesforce Account:** if no URL is known, omit the entire `**Salesforce Account:**` line; never write `N/A`, never invent a URL.
  - **References:** drop any bullet whose link is unknown; if both are unknown, write the section's content as `N/A`.
- `Customer-Stated Priority` must be one of `Critical` / `High` / `Medium` / `Low`. When inferred (not customer-stated), note the inference in the Problem Statement.
- For any other section with no applicable content, write `N/A` rather than omitting the section.

**Writing style (audience: Mattermost product managers)**
- Assume product literacy but no ticket context. Lead with the customer's actual ask; a PM should grasp it in the first two sentences.
- Be specific about scope: what the feature does, what it does not do, and where it fits (config, UI, API, plugin).
- Frame the problem in product terms (user impact, frequency, affected persona), not support terms (ticket noise). PMs prioritize on user value and reach.
- Surface signals a PM cares about: users/customers affected, blocker vs. friction, revenue/renewal tie-in, competitor parity.
- No vague language ("may", "might", "could be useful"); state conditions explicitly.
- Do not propose implementation details unless the customer asked; PMs decide solution shape.
- The whole post should fit one screen; a PM should triage it in under 60 seconds.
- No preamble before or after the post.

**Phase 3 - Review before posting**
- If the user asks to post to a channel or thread, render the draft first and ask for confirmation before sending.

<post_template>
# Feature Request: [Customer] - [Short, Descriptive Title]

**Customer:** [Company Name]  
**Contact:** [First Surname][, Title if known][, email if known]  
**Zendesk Ticket:** [#ID](URL)  
**Hub Post:** [Label](URL)  
**Jira Ticket:** [KEY](URL)  
**Salesforce Account:** [Company Name](URL)  
**Customer-Stated Priority:** `Critical` / `High` / `Medium` / `Low`  

---

## Summary
_One or two sentences describing the feature at a high level._

---

## Problem Statement
**Who is affected?**  
_e.g., Team admins, end users, enterprise customers_

**What is the current pain point?**  
_Describe what users are struggling with today. Include any workarounds they currently use._

**How often does this come up?**  
_e.g., Reported by X customers, seen in Z support tickets, recurring theme in user interviews_

---

## References
- Mattermost thread: [Label](URL)
- Related issues: [Label](URL)
</post_template>
