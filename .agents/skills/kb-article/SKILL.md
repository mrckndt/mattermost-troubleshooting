---
name: kb-article
description: Generate a KB article from the current troubleshooting context. Optional arg: ticket ID (tickets/<name>/) or problem/solution description to factor in.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Generate a knowledge-base article for the current troubleshooting context, and save it to disk.

## Phase 0 - Resolve save location

1. `$ARGUMENTS` matches an existing directory under `tickets/` (check with
   `ls "$PROJECT_ROOT/tickets/$ARGUMENTS"`): **ticket mode**, `<ID>=$ARGUMENTS`.
2. Otherwise, if `$ARGUMENTS` contains a `tickets/<name>/` path reference anywhere in the text
   and that directory exists: **ticket mode**, `<ID>=<name>`.
3. Otherwise, if this conversation has already been working a specific ticket (its files were
   read earlier in this session, e.g. via `/investigate`): **ticket mode** with that `<ID>`.
4. Otherwise: **no-ticket mode**.

Save targets:
- **Ticket mode:** `tickets/<ID>/kb-article.md`, `tickets/<ID>/kb-article.html`.
- **No-ticket mode:** `kb-articles/<slug>-<date>.md`, `kb-articles/<slug>-<date>.html`, where
  `<slug>` is a kebab-case slug of the article's `##` topic heading and `<date>` is today's
  date (`date +%Y-%m-%d`). Create `kb-articles/` at the project root if it doesn't exist yet.

## How to reason

1. Review everything known: the conversation, logs, config, error messages, and (in ticket
   mode) `tickets/<ID>/` files per Phase 1's first step.
2. If $ARGUMENTS is provided, treat it as additional context or direction and incorporate it.
3. Follow the four phases below in order.

## KB article format rules (apply these exactly)

**Phase 1 - Gather inputs**
- In ticket mode (Phase 0 resolved an `<ID>`): always read `tickets/<ID>/hub-thread.md` and
  `tickets/<ID>/analysis.md` (or `analysis-full.md`), whichever exist, regardless of what this
  conversation already covered.
- Check whether the following are known from the conversation:
  - Product and version(s) affected (e.g., Mattermost Server v9.x, Mattermost Cloud)
  - Problem description
  - Observable symptoms (errors, logs, UI behavior)
  - Solution/resolution steps
  - Warnings, caveats, or security considerations
  - Relevant external links
- Ask for any missing items. Ask at most one follow-up before proceeding with what is available.

**Phase 2 - Generate Markdown**
- Produce the article in Markdown following the template exactly. Do not add or remove sections.
- Output under a `##` heading summarizing the topic (e.g. "## LDAP Sync Fails After Upgrade to v9.5"). Print raw Markdown (not inside a code block) so it renders in Mattermost.
- Every template section must have content; use "N/A" rather than omitting a section.

**Phase 3 - Convert to HTML**
- Convert to HTML using only tags with direct Markdown equivalents (h1-h6, strong, em, del, code, a, p, img, ul, ol, li, blockquote, pre, hr, br, table, thead, tbody, tr, th, td, sup). No styling, classes, or wrapper divs.
- Do not print this HTML in the response; it exists only in the `.html` file Phase 4 writes.

**Phase 4 - Save**
- Write the Markdown from Phase 2 (including its `##` heading) to the `.md` save target resolved in Phase 0.
- Write the HTML from Phase 3 to the `.html` save target.
- Overwrite in place if either file already exists.
- After the Markdown in the response, append one line: `Saved to: <md path>, <html path>`.

**Writing style**
- Second person ("you", "your"). Present tense for instructions ("Navigate to...", not "You should navigate to...").
- Include the full navigation path for settings (e.g., **System Console > Environment > Web Server**).
- No vague language ("may", "might", "sometimes"); state conditions explicitly.
- Keep the **Symptoms** header field to one sentence; put detail in the `### Symptoms` section.
- No preamble before or after the article.

<article_template>
**Applies to:** [Product Name and version, e.g., "Mattermost Server v9.0 and later" or "Mattermost Cloud"]

**Symptoms:** [One-sentence summary of the issue from a sysadmin's perspective]

---

## 🛑 Problem

[Description of the problem. Be precise and technical. Write for a system administrator, not an end user.]

### Symptoms

Users or administrators experiencing this issue will see:

```
[Exact error message or log output if available]
```

Additional symptoms:
- [Symptom 1]
- [Symptom 2]
- [Symptom 3]

---

## ✅ Solution

[Overview of what the solution does and why it works.]

### [Step Title - use an action verb, e.g., "Update the System Console Setting"]

[Step instructions. Use **bold** for UI labels, config keys, or values the admin must enter exactly.]

```
[Command, config snippet, or code example if applicable]
```

> ⚠️ **Important:** [Any security considerations, destructive actions, restart requirements, or caveats the admin must be aware of.]

[Repeat ### Step Title blocks as needed for multi-step solutions.]

### Additional Resources

For more information, see:

[Link Label](https://url)
</article_template>
