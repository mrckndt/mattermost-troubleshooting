---
name: eir
description: Generate an internal Engineering Incident Report for a ticket: full eir.md plus a compact channel-post summary, grounded in analysis.md and GitHub/Jira lookups. Optional arg: ticket ID.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Generate an internal Engineering Incident Report (EIR) for a ticket.

## Phase 0 - Resolve ticket

1. Run `/resolve-ticket-id $ARGUMENTS` inline; ID returned: `<ID>` = that value.
2. Otherwise, if `$ARGUMENTS` contains a `tickets/<name>/` path reference and that directory exists: `<ID>=<name>`.
3. Otherwise, if this conversation has already been working a specific ticket (its files were read
   earlier in this session, e.g. via `/investigate`): use that `<ID>`.
4. Otherwise: ask the engineer for the ticket ID (or its `tickets/<name>/` path) before proceeding -
   this report requires `tickets/<ID>/analysis.md` and can't be produced without a resolved ticket directory.

Save target: `tickets/<ID>/eir.md`.

## Your task

1. Read `tickets/<ID>/analysis.md` as your primary source of truth. Do not speculate or add
   information that is not grounded in the analysis or artifacts from this ticket directory.

2. If `analysis.md` is missing or incomplete, say so and ask whether to run `/investigate <ID>`
   first before proceeding.

3. Search `tickets/<ID>/` (and subdirectories) for any additional artifacts that may add relevant
   detail - config.json, DB query output, node logs, etc.

4. Look for related issues, PRs, or known bugs that should be referenced in the report:
   - GitHub: `mcp__claude_ai_GitHub_MCP__*`. Jira: `mcp__claude_ai_Atlassian__*` (project `MM` only).
   - Per `AGENTS.md`'s boundary: query with generic technical terms only (error message templates,
     function/symbol names, config keys) - never a customer's hostname, domain, email, username,
     org name, or other identifying detail pulled from the ticket.
   - If a tool is absent, state `GitHub search skipped: MCP not available` / `Jira search skipped:
     MCP not available` and continue; never block.

5. Produce two outputs:

   **a) Full EIR** - Write to `tickets/<ID>/eir.md` using the detailed format below. This is the
   attachment for anyone who wants the full picture.

   **b) Channel post** - Print a compact summary to the screen (do NOT write it to a file). This is
   what gets pasted into the Mattermost channel. Keep it short enough that an engineer will
   actually read it in-line.

After writing `eir.md`, print `Saved to: tickets/<ID>/eir.md` (the channel post itself is printed
only, never saved).

---

## Full EIR format (`eir.md`)

```markdown
# Engineering Incident Report — <one line description>

**Ticket:** <number>
**Mattermost version:** <from logs or config>
**Deployment:** <Docker / K8s / bare metal / Cloud>
**Status:** <Investigating / Resolved / Monitoring>

---

## Summary

Three to four sentences max. What happened, what was the impact, and what the
root cause is (or that it is still under investigation).

---

## Detailed analysis

Walk through the issue like a bug report's "steps to reproduce":

1. **The error** — The specific problem. Exact error messages with timestamps.

2. **The cause** — What code path, config, or infrastructure is responsible.
   Cite file paths, function names, or config keys. Include brief code
   excerpts or links where helpful.

3. **The evidence** — Log lines, config values, timeline correlations, or
   code behavior that support the conclusion. Include relevant log excerpts
   inline. Link any related GitHub issues, PRs, or Jira tickets.

4. **Open questions** — Anything unconfirmed or needing further investigation.
   What additional information would help.

If there are multiple distinct issues, repeat this structure for each one
under its own subheading.
```

---

## Channel post format (printed to screen)

This is the compact version engineers see in the channel. Write it as a single
prose paragraph — no headings, no bold labels, no bullet points. It should read
like a concise technical narrative that an engineer can absorb in one pass.

Structure the paragraph as:

1. **Open with the customer-facing symptom** — what the user actually
   experiences.
2. **Explain the technical mechanism** — what is actually happening under the
   hood and why.
3. **Include key numbers and evidence inline** — specific values, sizes, limits,
   thresholds, error counts. These make the explanation concrete.
4. **Close with the gap or implication** — what's missing, what differs between
   clients/paths, or what needs to happen.

Rules:
- One paragraph, roughly 4-6 sentences
- Plain prose — no markdown formatting, no labels, no structure
- Concrete and specific — prefer exact numbers and config values over vague
  descriptions
- Do not include the ticket number, version, or status — those are in the
  full report
- Do not include customer-identifying information

---

## Tone and style guidelines

- Technical depth goes in `eir.md` — the channel post is a headline
- Be direct about what went wrong — this is an internal document
- Do not soften findings or omit embarrassing details
- Do not include customer-identifying information (company name, contact names)
- If something is unknown or unconfirmed, say so explicitly rather than
  speculating
