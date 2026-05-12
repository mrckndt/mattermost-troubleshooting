---
description: Switch a cloned repo under upstream/ to a tag or branch (no ref = default branch)
argument-hint: <repo> [<ref>]
---

First verify the shell is at the project root - a prior skill/tool may have left it in a subdirectory, silently misrouting relative paths like `upstream/<repo>`. Run `pwd && ls -1 CLAUDE.md README.md .gitignore .claude claude-md upstream`. If `pwd` doesn't end in `/mattermost-troubleshooting` or any entry is missing, `cd` (absolute path) to the root before continuing.

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

5. **Graphify post-switch update.** Run only if `command -v graphify` succeeds AND `graphs/config.json` exists AND `graphs/<repo>/graphify-out/graph.json` exists. Otherwise append a single line `Graph: skipped (<reason>).` to the report and continue.
   - Read the pre-switch ref from `graphs/<repo>/.meta.json` (`ref` field). The post-switch ref is the new HEAD sha (`git -C upstream/<repo> rev-parse HEAD`). If they match (no actual code change), set `Graph: skipped (HEAD unchanged)` and skip to the cascade only if other repos cascade into shared bundles - but in this single-repo command, just skip and stop.
   - Capture `old_nodes` (node count from existing graph.json), then run the update per scope from `graphs/config.json#/repos/<repo>/scope`:
     - For `scope: full`: `cd <abs-path>/graphs/<repo> && graphify update <abs-path>/upstream/<repo>` (single chained Bash call so graphify writes to the intended CWD). Re-extracts code via AST (no LLM calls).
     - For `scope: subdirs`: for each subdir path in `graphs/config.json#/repos/<repo>/paths` with changed files (`git -C upstream/<repo> diff --name-only <old-ref>..HEAD -- <subdir-path>`), run `cd <abs-path>/graphs/<repo>/<subdir-name> && graphify update <abs-path>/upstream/<repo>/<subdir-path>` where `<subdir-name>` is `<subdir-path>` with `/` replaced by `_`. After all changed subdirs are updated, re-merge and re-cluster: `graphify merge-graphs graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json`, then `graphify cluster-only graphs/<repo>/ --no-viz`.
   - Update `graphs/<repo>/.meta.json` with the new ref and current ISO timestamp.
   - Read `new_nodes` from the updated graph.json; `Δ = new_nodes - old_nodes`.
   - **Cascade**: re-run `graphify merge-graphs ... --out graphs/_bundles/<bundle>/graphify-out/graph.json` then `graphify cluster-only graphs/_bundles/<bundle>/ --no-viz` for every bundle whose `repos` list contains this repo and whose full member set is built. Then re-merge `graphs/_all/graphify-out/graph.json` from every existing per-repo graph.json and re-cluster with `--no-viz`.
   - Append a single line to the report: `Graph: updated <Δ> nodes. Cascade: <comma-separated _bundles/<bundle> entries plus _all|none>.`
   - If any step fails, surface the failure on the same line (e.g. `Graph: updated +12. Cascade: _bundles/<bundle>: cluster failed.`) and continue. Do not abort the command for a graphify failure.

Do NOT auto-revert at the end of the turn. Leave the repo on the chosen ref so follow-up questions can keep reading code at that version.
