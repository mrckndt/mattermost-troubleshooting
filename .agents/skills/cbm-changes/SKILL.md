---
name: cbm-changes
description: Show the blast radius of a diff in a codebase-memory-indexed repo - which symbols a change affects, risk-classified.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] [<since-ref>]`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and any remaining text is `<since-ref>` (a git tag/branch/sha to diff against, e.g. an older version tag vs. the currently checked-out one).
- Otherwise, `<repo>` defaults to `mattermost` and any remaining text is `<since-ref>`.
- No `<since-ref>`: diffs the working tree's uncommitted changes.

1. Run `/cbm-index <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. Call `detect_changes` with `project`, `since` = `<since-ref>` if given, `depth: 2`.
3. If `<since-ref>` was given and `changed_count` is 0, verify before trusting it: run `git -C "$PROJECT_ROOT/upstream/<repo>" diff --stat <since-ref> 2>&1` (no `--` before a ref - `git diff --stat <ref> -- HEAD` misparses `HEAD` as a pathspec and silently returns nothing). `detect_changes`'s `since` mode is unreliable against historical refs (it appears to only reliably diff uncommitted working-tree changes, despite its parameter description citing a tag example) - if `git diff` shows changes that `detect_changes` missed, say so plainly and present the `git diff --stat` output instead of reporting "no changes".
4. Present affected symbols grouped by risk classification (CRITICAL/HIGH/MEDIUM/LOW).
