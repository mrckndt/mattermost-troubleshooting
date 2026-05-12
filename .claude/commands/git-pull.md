---
description: Run git pull --ff-only on the current branch of one repo (arg) or every repo under upstream/ (no arg)
argument-hint: [<repo>]
---

First verify the shell is at the project root - a prior skill/tool may have left it in a subdirectory, silently misrouting relative paths like `upstream/<repo>`. Run `pwd && ls -1 CLAUDE.md README.md .gitignore .claude claude-md upstream`. If `pwd` doesn't end in `/mattermost-troubleshooting` or any entry is missing, `cd` (absolute path) to the root before continuing.

Args: optionally a single `<repo>` name (matching a directory under `upstream/`).

Determine the target set:
- If an argument is given: verify `upstream/<repo>/` exists. If not, list available repos under `upstream/` and stop. Otherwise process just that one repo.
- If no argument is given: process every repo under `upstream/`.

For each repo in the target set:

1. Run `git -C upstream/<repo> pull --ff-only`. Let git handle upstream resolution, detached HEAD, dirty tree, missing remote ref, etc. - whatever git says, report. Do not pre-check or guard.
2. Run `git -C upstream/<repo> rev-parse --abbrev-ref HEAD` to capture the current branch (`HEAD` means detached - report it as `(detached)`).
3. Continue to the next repo on any error.

Report a Markdown table with one row per repo and the columns: `Repo | Branch | Pull | Graph | Cascade`.
- `Branch`: from `rev-parse --abbrev-ref HEAD` (or `(detached)`).
- `Pull`: `up to date`, `updated <oldsha>..<newsha>`, or the error message git printed.
- `Graph` and `Cascade`: see "Graphify update cascade" below. If graphify is not installed, leave both blank for every row.

After processing the target set, mark each repo touched as fetched-this-session so the auto-lazy fetch policy in `CLAUDE.md` does not refetch it later in this conversation.

## Graphify update cascade

Run only if `command -v graphify` succeeds AND `graphs/config.json` exists. Otherwise leave the `Graph` and `Cascade` columns blank and skip silently (do not fail the pull).

For each repo whose `Pull` result is `updated <oldsha>..<newsha>` (HEAD moved):

1. If `graphs/<repo>/graphify-out/graph.json` does NOT exist, set `Graph = n/a (not built)` and skip the per-repo update for this row. Cascade row entry: `none`.
2. If `graphs/<repo>/graphify-out/graph.json` exists, capture `old_nodes` (node count from the existing graph.json), then run the update per the repo's scope from `graphs/config.json#/repos/<repo>/scope`:
   - For `scope: full`: run `cd <abs-path>/graphs/<repo> && graphify update <abs-path>/upstream/<repo>` (chained in one Bash call so graphify writes to the intended CWD). Re-extracts code via AST (no LLM calls). Doc/paper/image changes accumulate until the next full rebuild.
   - For `scope: subdirs`: for each subdir path in `graphs/config.json#/repos/<repo>/paths` with changed files (`git -C upstream/<repo> diff --name-only <oldsha>..<newsha> -- <subdir-path>`), run `cd <abs-path>/graphs/<repo>/<subdir-name> && graphify update <abs-path>/upstream/<repo>/<subdir-path>` where `<subdir-name>` is `<subdir-path>` with `/` replaced by `_`. After all changed subdirs are updated, re-merge and re-cluster the top-level graph: `graphify merge-graphs graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json`, then `graphify cluster-only graphs/<repo>/ --no-viz`.
   - Update `graphs/<repo>/.meta.json` with the new HEAD sha and the current ISO timestamp.
   - Read `new_nodes` from the updated graph.json. Set `Graph = updated <Δ> nodes` where `Δ = new_nodes - old_nodes` (signed, e.g. `+12`, `-3`, `0`).
3. If `Pull` is `up to date` and `graphs/<repo>/graphify-out/graph.json` exists, set `Graph = skipped (unchanged)`.
4. If `Pull` errored, set `Graph = skipped (pull failed)`.

After per-repo updates, compute the cascade set:

5. **Bundles**: read `graphs/config.json#/bundles`. Any bundle whose `repos` list contains at least one repo that was rebuilt in step 2 is "affected". For each affected bundle whose member set is fully built, re-run `graphify merge-graphs <member graph.json files> --out graphs/_bundles/<bundle>/graphify-out/graph.json` then `graphify cluster-only graphs/_bundles/<bundle>/ --no-viz`.
6. **`_all`**: if ANY repo was rebuilt in step 2, re-merge every existing per-repo `graph.json` into `graphs/_all/graphify-out/graph.json` then `graphify cluster-only graphs/_all/ --no-viz`.
7. Populate the `Cascade` column on each updated repo's row with a comma-separated list of the bundles + `_all` that re-merged because of that repo. Rows with `Graph = skipped (unchanged|pull failed)` or `n/a (not built)` get `Cascade = none`.

If a cascade merge or cluster step fails for a bundle / `_all`, report the failure inline in the affected rows' `Cascade` column (e.g. `_bundles/calls: cluster failed`) and continue. Do not abort the cascade for one failure.

Notes:
- Run each git invocation as a separate Bash tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`. Parallelize across repos in a single message. Exception: `cd <graphs/dir> && graphify update <upstream/path>` must stay chained in a single Bash call so graphify writes to the intended CWD.
- This command does NOT refresh tags or other branches. If you need new tags (e.g., before `/git-switch <repo> <tag>`), do a one-off `git -C upstream/<repo> fetch --tags` first.
- The graphify update is best-effort. If it fails for a repo, the pull is still considered successful; the `Graph` column captures the failure reason.
