---
description: Switch a cloned repo under upstream/ to a tag or branch (no ref = default branch)
argument-hint: <repo> [<ref>]
---

Args: $ARGUMENTS

Parse the args as `<repo> [<ref>]`. Switch the working tree of `upstream/<repo>` to `<ref>` (or restore the default branch if `<ref>` is omitted).

Steps:

1. Verify `upstream/<repo>/` exists. If not, list available repos under `upstream/` and stop.
2. Run `git -C upstream/<repo> status -s`. If non-empty, refuse the switch and report the local changes (advise the user to commit, stash, or discard before retrying).
3. Switch. No upfront fetch; only fetch as a fallback if the ref is unknown locally:
   - If `<ref>` is empty: resolve the default branch via `git -C upstream/<repo> symbolic-ref refs/remotes/origin/HEAD --short`, strip the `origin/` prefix, then run `git -C upstream/<repo> switch <default>`.
   - Otherwise:
     a. Try `git -C upstream/<repo> switch <ref>` (succeeds if `<ref>` is a known local branch).
     b. If (a) fails, try `git -C upstream/<repo> switch --detach <ref>` (succeeds if `<ref>` is a known local tag or commit).
     c. If (b) also fails (the ref isn't known locally at all), run `git -C upstream/<repo> fetch --tags --prune` once, then repeat (a) and (b).
   - Do not pre-check whether the ref is a tag - let git decide.
4. Report the new state by reformatting `git switch`'s own output so it includes the repo path. Replace the leading `Switched ` (or `HEAD is now at ...`) phrasing with `Switched upstream/<repo> to ...`, preserving the rest verbatim. Examples:
   - git says `Switched to branch 'master'` -> report `Switched upstream/mattermost to branch 'master'`.
   - git says `Switched to a new branch 'release-11.5'` -> report `Switched upstream/mattermost to a new branch 'release-11.5'`.
   - For a detached tag checkout (e.g. `git switch --detach v10.5.1`), git prints `HEAD is now at <sha> ...`; report `Switched upstream/<repo> to detached HEAD on tag 'v10.5.1' (<sha>)`.
   Do NOT call `describe --tags --always` or any other extra git command for the report.

Do NOT auto-revert at the end of the turn. Leave the repo on the chosen ref so follow-up questions can keep reading code at that version.
