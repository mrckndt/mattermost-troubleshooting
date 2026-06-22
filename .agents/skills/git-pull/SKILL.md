---
name: git-pull
description: Run git pull --ff-only on the current branch of one repo (arg) or every repo under upstream/ (no arg)
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: optionally a single `<repo>` name matching a directory under `upstream/`.

- If an argument is given: verify `upstream/<repo>/` exists (if not, list available repos and stop). Process that repo only.
- If no argument: process every repo under `upstream/`.

For each repo:

1. `git -C "$PROJECT_ROOT/upstream/<repo>" pull --ff-only`. Report whatever git says; do not pre-check or guard.
2. `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD` to capture the branch (`HEAD` = detached, report as `(detached)`).
3. Continue on error.

Report a Markdown table: `Repo | Branch | Pull`.
- `Pull`: `up to date`, `updated <oldsha>..<newsha>`, or the git error.

Notes:
- Run each git invocation as a separate Bash tool call; do not chain or append `2>&1`. Parallelize across repos in a single message.
- This command does NOT refresh tags. For new tags before `/git-switch`, run `git -C "$PROJECT_ROOT/upstream/<repo>" fetch --tags` first.
