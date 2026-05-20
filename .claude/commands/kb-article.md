---
description: Generate a KB article from the current troubleshooting context. Optional arg: problem/solution description to factor in.
argument-hint: [problem or solution description]
---

Args: $ARGUMENTS

Generate a knowledge-base article for the current troubleshooting context.

## How to reason

1. Review everything known: `./tickets/<name>/` files, the conversation, logs, config, error messages.
2. If $ARGUMENTS is provided, treat it as additional context or direction and incorporate it.
3. Follow the three phases below in order.

## KB article format rules (apply these exactly)

**Phase 1 - Gather inputs**
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
- Label this block "# 📋 Article HTML" and wrap in a fenced code block so it can be copied without rendering.

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

