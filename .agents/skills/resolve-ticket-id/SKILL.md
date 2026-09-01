---
name: resolve-ticket-id
description: Normalize a ticket reference (bare number, zd-prefix, ZD- form, Zendesk URL) to a numeric ID; verifies tickets/<id>/ exists unless --allow-new. Returns the ID or "no-match".
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Strip `--allow-new` from `$ARGUMENTS` first, in any position; keep the remainder as the reference. Resolve it to a Zendesk ticket ID. Apply in order; stop at the first hit.

1. If the remainder is empty: emit `no-match` and stop.
2. Strip a leading `#` if present. Match case-insensitively to extract a numeric candidate:
   - Bare number: `^[0-9]+$`
   - `zd<num>` / `zd-<num>` / `ZD-<num>`: `^zd-?([0-9]+)$` (case-insensitive)
   - Zendesk agent URL: `mattermost\.zendesk\.com/agent/tickets/([0-9]+)` (matches even with trailing `?query` params, e.g. `?brand_id=327479`)
   - Generic `http(s)://` URL: strip any `?query` and `#fragment` first, then take the last all-digit path segment
   - No pattern matched: use the raw value as candidate (non-numeric directory name)
3. `--allow-new` set: emit the candidate and stop - for a caller (e.g. `/hub-harvest`) about to create `tickets/<candidate>/`, a missing directory is expected, not a failure.
   Otherwise check `ls "$PROJECT_ROOT/tickets/<candidate>"`:
   - Exists: emit the candidate and stop.
   - Missing: emit `no-match` and stop.

**Output:** exactly one line - the resolved ID (e.g. `51909`) or `no-match`. No other output.
