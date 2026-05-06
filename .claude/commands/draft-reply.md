---
description: Draft a customer reply (email, Zendesk, hub thread) based on the current troubleshooting context. Optional arg: problem/solution description to factor in.
argument-hint: [problem or solution description]
---

Args: $ARGUMENTS

Draft a customer-facing reply for the current troubleshooting context. The reply may be sent over email, Zendesk, or a Mattermost hub thread - the format below applies to all of them.

## How to reason

1. Review everything known about the ticket: files under `./tickets/<name>/`, the conversation so far, any logs or config already analysed.
2. If $ARGUMENTS is provided, treat it as additional context or direction (e.g. "root cause is X, fix is Y") and incorporate it into the reply.
3. Determine what the reply needs to cover:
   - A diagnosis, a request for more information, a fix/workaround, or a status update.
4. Draft accordingly. Do not pad. If something is uncertain, say so briefly rather than omitting it.

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

Mattermost serves US government customers, so outbound statements must not overstate certainty. Calibrate language to the evidence actually in hand.

- Do not present claims about product behavior, root cause, fixes, timelines, or version-specific details as definitive unless they are verified against documentation, source, or a tool result already cited in the conversation. When verified, you may state them plainly; when not, hedge.
- Use hedging language for unverified or partially supported claims: "based on the logs shared", "this appears to be", "likely", "in most deployments we've seen", "we believe", "pending confirmation". Avoid absolutes like "this will fix it", "this is guaranteed to", "always", "never" unless the supporting evidence is explicit.
- Frame recommended actions as the next step to try and what outcome would confirm or rule out the hypothesis, rather than as a guaranteed resolution.
- Do not commit on behalf of Mattermost to fixes, timelines, roadmap items, SLAs, or contractual outcomes. Defer those to the appropriate owner (engineering, product, account team, CSM).

## Output

Print only the reply text as Markdown, ready to copy-paste. No commentary before or after it.
