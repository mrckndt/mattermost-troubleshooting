---
description: Draft a customer reply (email, Zendesk, hub thread) based on the current troubleshooting context. Optional arg: problem/solution description to factor in.
argument-hint: [problem or solution description]
---

Args: $ARGUMENTS

Draft a customer-facing reply for the current troubleshooting context. The format below applies whether sent by email, Zendesk, or Mattermost hub thread.

## How to reason

1. Review everything known: `./tickets/<name>/` files, the conversation, logs, and config already analysed.
2. If $ARGUMENTS is provided, treat it as additional context or direction and incorporate it.
3. Determine what to cover: diagnosis, request for more information, fix/workaround, or status update.
4. Draft accordingly. Do not pad. State uncertainty briefly rather than omitting it.

## Reply format rules (apply these exactly)

**Greeting**
- If the customer's first name is known, use it: `Hello <FirstName>,`
- If not known: `Hello,`
- Use `Hey` instead of `Hello` only if the customer's own tone in prior messages is clearly informal.

**Body**
- Keep it as short as possible while remaining complete.
- Use numbered or bulleted steps for procedures (commands, config changes, sequences of actions).
- Use plain prose for everything else (diagnosis, explanations, status updates).
- No pleasantries, no filler ("Hope this helps!", "Great question!", etc.).

**Sign-off**
```
Best regards,
```
No name after it - the system signature will be appended automatically.

## Tone and certainty

Mattermost serves US government customers; do not overstate certainty. Calibrate language to the evidence in hand.

- Do not present product behavior, root cause, fixes, timelines, or version details as definitive unless verified against documentation, source, or a cited tool result. Hedge when not verified.
- Hedging language: "based on the logs shared", "this appears to be", "likely", "in most deployments we've seen", "we believe", "pending confirmation". Avoid absolutes ("this will fix it", "always", "never") without explicit supporting evidence.
- Frame recommended actions as the next step to try and what outcome confirms or rules out the hypothesis, not as a guaranteed resolution.
- Do not commit on behalf of Mattermost to fixes, timelines, roadmap items, SLAs, or contractual outcomes. Defer to the appropriate owner (engineering, product, account team, CSM).

## Output

Print only the reply text as Markdown, ready to copy-paste. No commentary before or after it.
