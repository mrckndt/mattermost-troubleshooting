---
name: cbm-detect-changes
description: List symbols defined in a diff's changed files in a codebase-memory-indexed repo. Wraps detect_changes.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] [<compare-ref>]`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and any remaining text is `<compare-ref>` (a git tag/branch/sha to diff against).
- Otherwise, `<repo>` defaults to `mattermost` and any remaining text is `<compare-ref>`.
- No `<compare-ref>`: diffs the working tree's uncommitted changes against the repo's default branch.

1. Run `/cbm-index-repository <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. Resolve the repo's actual default branch: `git -C "$PROJECT_ROOT/upstream/<repo>" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's#refs/remotes/origin/##'`.
   - `detect_changes`'s own `base_branch` default is the literal string `main`, not the repo's actual default.
   - Most repos under `upstream/` (including `mattermost`/`enterprise`) default to `master`.
   - Never omit `base_branch` and rely on the tool's default; always pass the resolved branch explicitly.
3. Call `detect_changes` with `project`, `scope: files`, `base_branch` = `<compare-ref>` if given, else the resolved default branch.
   - There is no `since` parameter on this tool. To diff against a version tag ("what changed between vX and vY"), pass that tag directly as `base_branch`.
   - `git diff --name-only <base_branch>...HEAD` accepts any valid ref, not just a branch name - a tag works fine here.
   - For two version tags on a linear history, `base_branch` must be the OLDER tag and the repo's checkout (`HEAD`) must be the NEWER one.
   - The reverse silently returns 0 changes (three-dot diff resolves from the merge-base, which equals the older ref either way).
   - `depth` is accepted but has no effect on the current tool version - it does not control any traversal. Do not rely on it to scope results.
   - It does **not** narrow by path/package; there is no path-scoping parameter on this tool.
4. Check `changed_count` first. There is no `limit` param on this tool - re-running without `scope: files` expands every changed file's full symbol list with no cap.
   - A major-version-spanning diff (hundreds of files) can overflow the response entirely (confirmed: a 433-file diff returned 500K+ characters and failed outright).
   - Only drop `scope: files` for the fuller symbol listing when `changed_count` is small (single digits to low tens).
5. Present `changed_files`, then (if fetched) `impacted_symbols` (flat `name`/`label`/`file` per symbol defined anywhere in a changed file).
   - This is **not** a transitive blast radius: it does not follow callers/callees.
   - It is also not scoped to the actual changed lines - touching one line at the end of a file lists every symbol in that whole file.
   - Use `/cbm-trace-path <repo> <symbol>` on any listed symbol to get its actual callers/callees.
6. If `changed_count` is 0 and that's surprising, cross-check before trusting it:
   - Run `git -C "$PROJECT_ROOT/upstream/<repo>" diff --stat <compare-ref-or-resolved-default-branch> 2>&1`.
   - No `--` before a ref: `git diff --stat <ref> -- HEAD` misparses `HEAD` as a pathspec and returns nothing.
   - If `git diff` shows changes `detect_changes` missed, say so plainly and present the `git diff --stat` output instead of reporting "no changes".
