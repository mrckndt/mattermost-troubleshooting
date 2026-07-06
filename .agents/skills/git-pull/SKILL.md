---
name: git-pull
description: Fetch tags and run git pull --ff-only on the current branch of one repo (arg) or every repo under upstream/ (no arg)
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: optionally a single `<repo>` name matching a directory under `upstream/`.

- If an argument is given: verify `upstream/<repo>/` exists (if not, list available repos and stop). Process that repo only.
- If no argument: process every repo under `upstream/`.

For each repo:

1. `git -C "$PROJECT_ROOT/upstream/<repo>" fetch --tags`. Refreshes all tags so a later `/git-switch <tag>` cannot resolve to a stale tag. Runs regardless of branch or detached HEAD.
2. `git -C "$PROJECT_ROOT/upstream/<repo>" pull --ff-only`. Report whatever git says; do not pre-check or guard.
3. `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD` to capture the branch (`HEAD` = detached, report as `(detached)`).
4. Continue on error.

Report a Markdown table: `Repo | Branch | Pull`.
- `Pull`: `up to date`, `updated <oldsha>..<newsha>`, or the git error.

Notes:
- Tags are refreshed as step 1, so `/git-switch <tag>` always sees the latest tags. A detached-HEAD repo still fetches tags even though its `pull --ff-only` reports no upstream branch.
