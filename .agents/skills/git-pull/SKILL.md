---
name: git-pull
description: Fetch tags and git pull --ff-only for the current branch: one repo (arg) or all repos under upstream/ (no arg).
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: optionally a single `<repo>` name matching a directory under `upstream/`.

- Argument given: verify `upstream/<repo>/` exists (if not, list available repos and stop); process that repo only.
- No argument: process every repo under `upstream/`.

For each repo, continue on error and move to the next:

1. `git -C "$PROJECT_ROOT/upstream/<repo>" fetch --tags`. Refreshes all tags so a later `/git-switch <tag>` cannot resolve to a stale tag. Runs regardless of branch or detached HEAD.
2. `git -C "$PROJECT_ROOT/upstream/<repo>" status -s`.
   - If non-empty: report the listed lines as changes about to be discarded.
   - Discard them: `git -C "$PROJECT_ROOT/upstream/<repo>" reset --hard`, then `git -C "$PROJECT_ROOT/upstream/<repo>" clean -fd`. Continue once clean.
3. `git -C "$PROJECT_ROOT/upstream/<repo>" pull --ff-only`. Report whatever git says; do not pre-check or guard.
4. `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD` to capture the branch (`HEAD` = detached, report as `(detached)`).

Report a Markdown table: `Repo | Branch | Pull`.
- `Pull`: `up to date`, `updated <oldsha>..<newsha>`, or the git error.

Note: a detached-HEAD repo still fetches tags in step 1 even though its `pull --ff-only` in step 3 reports no upstream branch.
