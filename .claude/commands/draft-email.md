---
description: Draft a customer reply email based on the current troubleshooting context. Optional arg: problem/solution description to factor in.
argument-hint: [problem or solution description]
---

Args: $ARGUMENTS

Draft a customer-facing reply email for the current troubleshooting context.

## How to reason

1. Review everything known about the ticket: files under `./tickets/<name>/`, the conversation so far, any logs or config already analysed.
2. If $ARGUMENTS is provided, treat it as additional context or direction (e.g. "root cause is X, fix is Y") and incorporate it into the email.
3. Determine what the email needs to cover:
   - A diagnosis, a request for more information, a fix/workaround, or a status update.
4. Draft accordingly. Do not pad. If something is uncertain, say so briefly rather than omitting it.

## Email format rules (apply these exactly)

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

## Output

Print only the email text as Markdown, ready to copy-paste. No commentary before or after it.
