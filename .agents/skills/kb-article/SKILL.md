---
name: kb-article
description: Generate a KB article from the current troubleshooting context. Optional arg: ticket ID (tickets/<name>/) or problem/solution description to factor in.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Generate a knowledge-base article for the current troubleshooting context, and save it to disk.

## Phase 0 - Resolve save location

1. Run `/resolve-ticket-id $ARGUMENTS` inline; ID returned: **ticket mode**, `<ID>` = that value.
2. Otherwise, if `$ARGUMENTS` contains a `tickets/<name>/` path reference and that directory exists: **ticket mode**, `<ID>=<name>`.
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
  `tickets/<ID>/analysis.md`, whichever exist, regardless of what this conversation already covered.
- Check whether the following are known from the conversation:
  - Product and version(s) affected
  - Problem description
  - Observable symptoms (errors, logs, UI behavior)
  - Solution/resolution steps
  - Warnings, caveats, or security considerations
  - Relevant external links
  - Fix status, and whether this is a confirmed defect, an advisory answer, or an open investigation - drives the Status field and the second-section heading below
- Ask for any missing items. Ask at most one follow-up before proceeding with what is available.

**Phase 2 - Generate Markdown**
- Follow the template below.
- Required: `**Applies to:**`, `**Symptoms:**`, `## 🛑 Problem`, exactly one second-section heading.
- The `**Symptoms:**` header field is always required, even when the `### Symptoms` subsection below is omitted - they are two different things with the same name.
- Optional: `**Status:**`, the whole `### Symptoms` subsection (heading and all), its code block, `> ⚠️ Important` blocks, `### Additional Resources`.
- **Omit rather than pad.** Never write `N/A` to fill a section or invent content to justify a heading.
- Output under a `##` heading summarizing the topic. Print raw Markdown (not in a code block).

**Second section - pick exactly one heading:**

| Heading | Use when |
|---|---|
| `✅ Solution` | Confirmed fix the admin applies (default case) |
| `🔧 Workaround` | Root cause known, no fix shipped; mitigation only |
| `💡 Recommendation` | Advisory: expected behavior or architecture guidance, no defect |
| `🔍 Diagnostic Steps` | Root cause not yet isolated; a procedure narrows it down |
| `🚧 Known Issue` | Nothing actionable for the customer yet; states the issue exists, no more |

- If the admin can do something, it is never `Known Issue`.
- `Known Issue` bans forward-looking language: no "will be updated", no ETA, no "check back".
- `Diagnostic Steps` and `Known Issue` both close with `### Contact Mattermost Support`. The other three never include it - they already give the admin an action.

**Problem: 2-4 sentences, one paragraph.** No sub-sections.
- Apply the delete test to every sentence: would the admin act differently without it? If not, cut it.
- Write what the admin observes, not what the code does. No evaluation order, guards, or fallbacks.
- No source symbols, `function:file` references, or runtime primitives (goroutines, mutexes) in prose. Verbatim quoted log or stack output is exempt.
- Depth is fine when it's load-bearing (it explains why the fix works), judged by the delete test, not by how technical it sounds.
- Cut material relocates, it isn't discarded:
  - An actionable cause becomes a Solution step.
  - Scope goes to `**Applies to:**` or a `### Symptoms` bullet.
  - Only mechanism with no admin consequence is dropped entirely.
- No SQL, shell, or command blocks in the Problem section. If a query or command proves the
  condition, it belongs in a verification step under the second section, not here.

**Symptoms:**
- Omit the whole subsection when there's nothing observable to report: a pure advisory question, an architecture recommendation, or an internal misconfiguration with no visible effect.
- Don't invent a symptom to fill it.
- When present, the code block is for verbatim machine output only. Omit it if none exists; never `N/A` or invented content.
- One bullet list. No "Additional symptoms:" split.
- Include misleading signals (things that look healthy but aren't) - the highest-value content here.

**Status field:**
- Optional, except required for `Known Issue` and any claim that can expire.
- Then carry an `as of <date>` qualifier, e.g. "Open, no fix available (as of 2026-08-05)".
- A shipped fix dates itself ("Fixed in v2.42.3") and needs no qualifier.
- Source the value from `analysis.md`'s `Resolution` section (in ticket mode), not from fresh
  reasoning; otherwise state only what's confirmed in the conversation and don't guess a version.

**Important blocks:**
- Only for a real caveat: destructive action, restart requirement, security implication, licensing gate, or a scope trap (a condition that's easy to miss, e.g. "this only fixes X, not Y").
- Max one per step, your own words, 1-3 sentences.
- Never paste a doc paragraph or leave a sentence truncated.

**Links - check every one before writing, inline and under Additional Resources:**
- Self-refresh before checking any `docs.mattermost.com` link: `/git-pull docs`. This skill can run
  standalone, without a prior `/investigate` in this session, so the local mirror may otherwise be
  arbitrarily stale relative to the live site.
- **In this repo, `docs.mattermost.com/<path>.html` links are locally checkable:** confirm
  `upstream/docs/docs/main/<path>.mdx` exists, and that any `#<anchor>` matches a real heading in
  that file (lowercased, punctuation/spaces to hyphens; MDX headings may also carry an explicit
  `{#custom-id}` override - check the file itself when the plain slug doesn't match before dropping
  the anchor). If the anchor doesn't match, link the page without it - never guess one. If the page
  itself doesn't exist, drop the link.
- For `support.mattermost.com`, `developers.mattermost.com`, and `github.com` links, which have
  no local source to check: if web search is available, use it to confirm a link before citing
  it. A single unclear result is not confirmation; don't cite on a weak match.
- Without a confirmed link, cite only one already in the conversation, or a well-established top-level product URL you're confident is correct.
- Never construct a specific article path, anchor, or ID from guesswork, confirmed or not - if unsure whether an anchor is correct, link the page without it.
- Never reference an internal Jira key.
- URLs with angle-bracket placeholders (e.g. `<tenant>`, `<mattermost-url>`) inside code blocks are exempt - they're deliberately not real.
- Omit Additional Resources entirely rather than link a bare domain root or repeat a link already cited inline.

**Phase 3 - Convert to HTML**
- Convert to HTML using only tags with a direct 1:1 Markdown equivalent:
  - `h1`-`h6`, `strong`, `em`, `del`, `code`, `a`, `p`, `img`, `ul`, `ol`, `li`
  - `blockquote`, `pre`, `hr`, `br`, `table`, `thead`, `tbody`, `tr`, `th`, `td`, `sup`
- No styling, classes, or wrapper divs.
- Do not print this HTML in the response; it exists only in the `.html` file Phase 4 writes.

**Phase 4 - Save**
- Write the Markdown from Phase 2 (including its `##` heading) to the `.md` save target resolved in Phase 0.
- Write the HTML from Phase 3 to the `.html` save target.
- Overwrite in place if either file already exists.
- After the Markdown in the response, append one line: `Saved to: <md path>, <html path>`.

**Writing style**
- Second person, present tense for instructions ("Navigate to...", not "You should navigate to...").
- Full navigation path for settings (e.g., **System Console > Environment > Web Server**).
- No vague language ("may", "might", "sometimes"); state conditions explicitly.
- Keep the **Symptoms** header field to one sentence; detail goes in `### Symptoms`.
- No preamble before or after the article.

<article_template>
**Applies to:** [Product and version range, plus any qualifying condition. One line.]

**Status:** [Optional; required for Known Issue. e.g. "Fixed in v2.42.3" / "Open, no fix available (as of 2026-08-05)"]

**Symptoms:** [Always required, even if the ### Symptoms subsection below is omitted. One-sentence summary from a sysadmin's perspective.]

---

## 🛑 Problem

[2-4 sentences, one paragraph. What the admin observes, under what condition, and why - at the level of things they can see or act on.]

### Symptoms [OMIT this whole subsection if there's nothing observable to report, e.g. a pure advisory question]

```
[Verbatim log line, error string, or API response. OMIT entirely if none exists.]
```

- [Observable behavior]
- [Scope boundary: what is and is not affected]
- [Misleading signal: something that looks healthy but is not]

---

## [Pick exactly one: ✅ Solution / 🔧 Workaround / 💡 Recommendation / 🔍 Diagnostic Steps / 🚧 Known Issue - see table above]

[1-2 sentences: what this delivers and what it does not.]

### [Step Title - action verb, e.g., "Update the System Console Setting"]

[Step instructions. **Bold** for UI labels, config keys, or exact values.]

```
[Command, config snippet, or code example if applicable]
```

> ⚠️ **Important:** [Only if there is a real caveat, in your own words.]

[Repeat ### Step Title blocks as needed, for Solution / Workaround / Recommendation.]

### Contact Mattermost Support [ONLY for Diagnostic Steps or Known Issue - omit entirely for the other three]

[Diagnostic Steps: recommend opening a case if these steps don't resolve or explain the issue. Known Issue: recommend opening a case so it can be tracked. 1-2 sentences.]

### Additional Resources [OMIT this whole section if there are no specific verified links]

[Link Label](https://url)
</article_template>
