---
description: Run git pull --ff-only on the current branch of one repo (arg) or every repo under upstream/ (no arg)
---

Args: optionally a single `<repo>` name (matching a directory under `upstream/`).

Determine the target set:
- If an argument is given: verify `upstream/<repo>/` exists. If not, list available repos under `upstream/` and stop. Otherwise process just that one repo.
- If no argument is given: process every repo under `upstream/`.

For each repo in the target set:

1. Run `git -C upstream/<repo> pull --ff-only`. Let git handle upstream resolution, detached HEAD, dirty tree, missing remote ref, etc. - whatever git says, report. Do not pre-check or guard.
2. Run `git -C upstream/<repo> rev-parse --abbrev-ref HEAD` to capture the current branch (`HEAD` means detached - report it as `(detached)`).
3. Continue to the next repo on any error.

Report a Markdown table with one row per repo and the columns: `Repo | Branch | Pull`.
- `Branch`: from `rev-parse --abbrev-ref HEAD` (or `(detached)`).
- `Pull`: `up to date`, `updated <oldsha>..<newsha>`, or the error message git printed.

After processing the target set, mark each repo touched as fetched-this-session so the auto-lazy fetch policy in `CLAUDE.md` does not refetch it later in this conversation.

Notes:
- Run each git invocation as a separate Bash tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`. Parallelize across repos in a single message.
- This command does NOT refresh tags or other branches. If you need new tags (e.g., before `/switch <repo> <tag>`), do a one-off `git -C upstream/<repo> fetch --tags` first.
