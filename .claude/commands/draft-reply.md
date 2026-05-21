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
Do not overstate certainty.

- Hedge only unverified claims about product behavior, root cause, or version-specifics. Verified facts: state plainly. One hedge per claim; no double-qualifying.
- Frame actions as next steps to try, not guaranteed fixes. Skip "what would confirm/rule out" framing unless asked.
- Defer fixes, timelines, and SLAs to the appropriate owner only when the customer asks about them.

## Output

Print only the reply text as Markdown, ready to copy-paste. No commentary before or after it.
