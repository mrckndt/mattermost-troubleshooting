---
description: Switch a cloned repo under upstream/ to a tag or branch (no ref = default branch)
argument-hint: <repo> [<ref>]
---

Apply the Shell conventions from `CLAUDE.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `<repo> [<ref>]`. Switch `upstream/<repo>` to `<ref>`, or the default branch if `<ref>` is omitted.

Steps:

1. Verify `upstream/<repo>/` exists; if not, list available repos and stop.
2. Capture the pre-switch HEAD sha: `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse HEAD`.
3. `git -C "$PROJECT_ROOT/upstream/<repo>" status -s`. If non-empty, refuse and report the changes (commit, stash, or discard before retrying).
4. Switch (no upfront fetch; fetch only as fallback):
   - If `<ref>` is empty: resolve the default branch via `git -C "$PROJECT_ROOT/upstream/<repo>" symbolic-ref refs/remotes/origin/HEAD --short` (strip `origin/` prefix), then `git switch <default>`.
   - Otherwise: (a) `git switch <ref>`; (b) if that fails, `git switch --detach <ref>`; (c) if both fail, `fetch --tags --prune` once then repeat (a) and (b). Do not pre-check whether the ref is a tag.
5. Report by reformatting `git switch`'s own output with the repo path prepended. Prefix `Switched upstream/<repo> to ...`, preserving the rest verbatim. Examples:
   - `Switched to branch 'master'` → `Switched upstream/mattermost to branch 'master'`.
   - `Switched to a new branch 'release-11.5'` → `Switched upstream/mattermost to a new branch 'release-11.5'`.
   - For a detached tag (`HEAD is now at <sha> ...`): `Switched upstream/<repo> to detached HEAD on tag 'v10.5.1' (<sha>)`.
   Do NOT call `describe --tags --always` or any other extra git command.

Do NOT auto-revert at the end of the turn. Leave the repo on the chosen ref for follow-up reads.
