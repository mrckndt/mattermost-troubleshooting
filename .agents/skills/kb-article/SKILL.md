---
name: kb-article
description: Generate a KB article from the current troubleshooting context. Optional arg: ticket ID (tickets/<name>/) or problem/solution description to factor in.
user-invocable: true
---

Args: $ARGUMENTS

Generate a knowledge-base article for the current troubleshooting context, and save it to disk.

## Phase 0 - Resolve save location

1. If `$ARGUMENTS` is already a bare ticket number (`^[0-9]+$`, the canonical Zendesk ID shape per
   `AGENTS.md`'s ID format contract) and `tickets/<that number>/` exists, skip `/resolve-ticket-id`:
   **ticket mode**, `<ID>` = that value directly. Otherwise, apply `/resolve-ticket-id`'s normalization rules (`.agents/skills/resolve-ticket-id/SKILL.md`)
   to `$ARGUMENTS` directly, in this same reasoning step - do not invoke it as a nested skill call. ID
   returned: **ticket mode**, `<ID>` = that value.
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
- In ticket mode (Phase 0 resolved an `<ID>`): always read `tickets/<ID>/zendesk-thread.md` (or legacy
  `hub-thread.md`) and `tickets/<ID>/analysis.md`, whichever exist, regardless of what this conversation
  already covered.
- Check whether the following are known from the conversation:
  - Product and version(s) affected
  - Problem description, or the question asked
  - Observable symptoms (errors, logs, UI behavior)
  - Solution/resolution steps, with prerequisites and how to verify them
  - Warnings, caveats, or security considerations
  - Relevant external links
  - Fix status, and whether this is a confirmed defect, an advisory answer, or an open investigation - drives the article
    type, the Status field, and the second-section heading below
  - Confidence: which claims `analysis.md` records as confirmed and which as hypothesis
- Ask for any missing items. Ask at most one follow-up before proceeding with what is available.

**Phase 2 - Generate Markdown**
- Follow the template below.
- Required: `**Applies to:**`, the header field and first section of the article type, exactly one second-section heading.
- Optional: `**Status:**`, the whole `### Symptoms` subsection (heading and all), its code block, `> ⚠️ Important` blocks,
  `### Additional Resources`.
- **Omit rather than pad.** Never write `N/A` to fill a section or invent content to justify a heading.
- **Confidence:** state a hypothesis from `analysis.md` as a condition the admin can check ("If the paired warning shows
  `broken pipe`, ..."), never as fact.
- Output under a `##` heading summarizing the topic. Print raw Markdown (not in a code block).

**Article type - pick one; it sets the header field and the first section:**

| Type | Use when | Header field | First section |
|---|---|---|---|
| Issue | Something fails or misbehaves: defect, misconfiguration, environment state, performance | `**Symptoms:**` | `## 🛑 Problem`, optional `### Symptoms` |
| Advisory | A question, no fault: CVE or compatibility applicability, "expected or harmful?", "can I...?", availability, sizing | `**Context:**` | `## 👓 Overview`, no `### Symptoms` |

- Pick by what the customer needed, not by `analysis.md`'s `Ticket type`: a log line sent as "is this harmful?" is
  Advisory, even when investigated as a fault.
- A ticket with both (a defect plus how-to questions) is Issue; answer the questions inside its steps.
- `**Symptoms:**` is one sentence from a sysadmin's perspective. `**Context:**` is one sentence on who asks and why
  (e.g. "Guidance for security teams evaluating PHP-related CVEs.").

**First section, both types: one paragraph, 2-4 sentences.** No sub-sections other than `### Symptoms`.
- **Problem (Issue):** what goes wrong, under which condition, and why, in one sentence at the level the admin can see
  or act on (e.g. "each upload over 50 MB leaves a temporary file in `/tmp`").
- **Overview (Advisory):** open with the answer as a bold sentence (e.g. **PHP CVEs do not apply to Mattermost
  Server.**), then the reason it holds, at the depth the reader needs to trust it. A bold lead-in label may open the
  reasoning (e.g. **Why this holds:**).
- **Bold** the facts that decide whether the article applies to the reader: version cutoff, platform, trigger.
- Apply the delete test to every sentence: would the admin act differently without it? If not, cut it.
- Describe causes as conditions, not code paths: no evaluation order, guards, or fallbacks.
- No source symbols, `function:file` references, or runtime primitives (goroutines, mutexes) in prose. Verbatim quoted log or stack output is exempt.
- Depth is fine when it's load-bearing (it explains why the fix works), judged by the delete test, not by how technical it sounds.
- Don't repeat the header field sentence; add to it.
- Cut material relocates, it isn't discarded:
  - An actionable cause becomes a step in the second section.
  - Scope goes to `**Applies to:**` or a `### Symptoms` bullet.
  - Only mechanism with no admin consequence is dropped entirely.
- No SQL, shell, or command blocks here. If a query or command proves the condition, it belongs in a step under the
  second section.

**Symptoms (Issue only):**
- Add only what the Problem and the header field don't already say: verbatim errors, scope boundaries, misleading signals.
- Omit the whole subsection when the Problem already covers everything observable, or when nothing is observable
  (an internal misconfiguration with no visible effect). Don't invent a symptom to fill it.
- When present, the code block is for verbatim machine output only, never a UI paraphrase or a log line already shown.
  Omit it if none exists; never `N/A` or invented content.
- One bullet list. No "Additional symptoms:" split.
- Include misleading signals (things that look healthy but aren't), led by `**Misleading:**` - the highest-value content here.

**Second section - pick exactly one heading:**

| Heading | Type | Use when |
|---|---|---|
| `✅ Solution` | Issue | The steps remove the cause: shipped fix, config correction, environment repair |
| `🔧 Workaround` | Issue | The cause is an unfixed defect; the steps only mitigate it |
| `🔍 Diagnostic Steps` | Issue | Root cause not yet isolated; a procedure narrows it down |
| `🚧 Known Issue` | Issue | Nothing actionable for the customer yet; states the issue exists, no more |
| `🛠️ How-To` | Advisory | A supported goal reached through a procedure: configuration, setup, sizing, migration |
| `💡 Recommendation` | Advisory | Guidance on expected behavior, applicability, or architecture; no procedure required |
| `🚫 Limitation` | Advisory | Not supported or by design; states the boundary, then the supported alternatives as steps |

- If the product defect remains after the steps, it is `Workaround`, even when the steps fully restore service.
- An environment the admin can repair (left-over state after a downgrade, a missing opt-in) is `Solution`, not `Workaround`.
- If the admin can do something, it is never `Known Issue`.
- `Known Issue` bans forward-looking language: no "will be updated", no ETA, no "check back".
- A `Solution` whose fix ships in a release may add a `### Until You Upgrade` step for interim mitigation.
- `Solution` and `Workaround` may end with `### If the Issue Persists`: the next cause to rule out (e.g. a proxy
  body-size limit recorded in `analysis.md`'s `Ruled out` or `Correlation`), then opening a case.
- `Diagnostic Steps` and `Known Issue` close with `### Contact Mattermost Support`. Advisory headings include neither closing section.

**Steps - what the second section must carry:**
- Open with 1-2 sentences: what this delivers and what it does not.
- Prerequisites (license tier, role, tool such as `mmctl`, network access) go in `**Applies to:**` or the first step,
  never discovered mid-procedure.
- Every admin action is a step. Never leave one only in a `### Symptoms` bullet or an Important block.
- Before a destructive step or a direct database edit, an Important block names the backup to take. For a
  reversible config change, one line says how to revert it.
- State a restart or reload requirement, bolded, in the step that needs it.
- Close `Solution`, `Workaround`, and `How-To` with a `### Verify ...` step naming the healthy state (metric, log line,
  UI check). Omit it only when nothing can be checked.
- In an upgrade step, bold the fixed-in version.

**Bold:**
- Bold the decisive facts: the answer, version cutoffs, platform or scope limits, the key action or "don't", restart
  requirements. Also UI labels, config keys, and exact values in steps.
- At most two decisive facts per paragraph or step; never a whole paragraph.

**Status field:**
- Optional, except required for `Known Issue`, `Limitation`, and any claim that can expire.
- Then carry an `as of <date>` qualifier, e.g. "Open, no fix available (as of 2026-08-05)".
- A shipped fix dates itself ("Fixed in v2.42.3") and needs no qualifier.
- No scheduled release dates or "under internal review": state only what is true today.
- Source the value from `analysis.md`'s `Resolution` section (in ticket mode), not from fresh
  reasoning; otherwise state only what's confirmed in the conversation and don't guess a version. If `Resolution`
  shows no released fix, an upgrade cannot be the `Solution`; use `Workaround`.

**Important blocks:**
- Only for a real caveat: destructive action, restart requirement, security implication, licensing gate, or a scope trap (a condition that's easy to miss, e.g. "this only fixes X, not Y").
- Max one per step, three per article, your own words, 1-3 sentences.
- Never paste a doc paragraph or leave a sentence truncated.

**Links - check every one before writing, inline and under Additional Resources:**
- Self-refresh before checking any `docs.mattermost.com` link: `/git-pull docs --interval=weekly`. This skill can run
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
- Omit Additional Resources entirely rather than link a bare domain root or repeat a link already cited inline. List at most
  three links, preferring docs and KB articles over pull requests.

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
- Keep the `**Symptoms:**` or `**Context:**` header field to one sentence; detail goes in the first section.
- No preamble before or after the article.

<article_template>
**Applies to:** [Product and version range, plus any qualifying condition or prerequisite. One line.]

**Status:** [Optional; required for Known Issue and Limitation. e.g. "Fixed in v2.42.3" / "Open, no fix available (as of 2026-08-05)"]

**Symptoms:** [Issue only. One-sentence summary from a sysadmin's perspective.]
**Context:** [Advisory only, in place of Symptoms. One sentence: who asks and why.]

---

## 🛑 Problem [Issue] / 👓 Overview [Advisory]

[2-4 sentences, one paragraph. Problem: what goes wrong, under which condition, and why. Overview: **the answer as a
bold sentence**, then why it holds. Bold the facts that decide whether this applies to the reader.]

### Symptoms [Issue only. OMIT if the Problem already covers everything observable]

```
[Verbatim log line, error string, or API response. OMIT entirely if none exists.]
```

- [Observable behavior not already in the Problem]
- [Scope boundary: what is and is not affected]
- **Misleading:** [something that looks healthy but is not]

---

## [Pick exactly one heading from the table above, matching the article type]

[1-2 sentences: what this delivers and what it does not.]

### [Step Title - action verb, e.g., "Update the System Console Setting"]

[Step instructions. **Bold** for UI labels, config keys, exact values, and the decisive fact.]

```
[Command, config snippet, or code example if applicable]
```

> ⚠️ **Important:** [Only if there is a real caveat, in your own words.]

[Repeat ### Step Title blocks as needed.]

### Verify [the Result] [Solution / Workaround / How-To: the healthy state to check. OMIT only if nothing can be checked]

### If the Issue Persists [Optional, Solution / Workaround only: next cause to rule out, then open a case]

### Contact Mattermost Support [ONLY for Diagnostic Steps or Known Issue]

[Diagnostic Steps: recommend opening a case if these steps don't resolve or explain the issue. Known Issue: recommend opening a case so it can be tracked. 1-2 sentences.]

### Additional Resources [OMIT this whole section if there are no specific verified links]

[Link Label](https://url)
</article_template>
