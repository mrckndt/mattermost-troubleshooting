---
description: Incrementally update one or more knowledge graphs. Per-repo runs graphify update; bundle runs merge + re-cluster.
argument-hint: [<repo> | <bundle-name> | --all]
---

First verify the shell is at the project root - a prior skill/tool may have left it in a subdirectory, silently misrouting relative paths like `graphs/<scope>`. Run `pwd && ls -1 CLAUDE.md README.md .gitignore .claude claude-md upstream graphs`. If `pwd` doesn't end in `/mattermost-troubleshooting` or any entry is missing, `cd` (absolute path) to the root before continuing. (If `graphs/` itself is missing, advise the user to run `/bootstrap` first - the rest of this command needs `graphs/config.json`.)

Source `.claude/secrets.env` if present so Python subprocesses inherit any project-scoped API keys (no-op if the file is absent). If neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` is set after sourcing, print the Gemini tip - `graphify update` may run semantic extraction for any non-code files that changed, and Gemini is the cheap path:

```
[ -f .claude/secrets.env ] && set -a && . .claude/secrets.env && set +a
if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
  echo "Couldn't source GEMINI_API_KEY or GOOGLE_API_KEY."
  echo "Tip: set GEMINI_API_KEY or GOOGLE_API_KEY to use Gemini for semantic extraction (pip install 'graphifyy[gemini]')."
  echo "Without it, semantic extraction falls back to Claude subagents (slower and more expensive)."
fi
```

Args: $ARGUMENTS

Behavior depends on the argument. Parse it into one of three modes:

- **No argument or `--all`**: update every built per-repo graph, then cascade all bundles. This is the "refresh everything" mode.
- **`<repo>`**: matches a name under `graphs/config.json#/repos`. Update that one repo's graph, then cascade bundles containing it.
- **`<bundle-name>`**: matches a name under `graphs/config.json#/bundles` AND `graphs/_bundles/<bundle-name>/graphify-out/graph.json` exists. Re-merge + re-cluster that bundle only (does not update the member repos first; assumes they are current).

If the argument doesn't match any of the above, enumerate the built scopes (same logic as `/graphify-scope` with no argument) and stop with: `Target '<arg>' not found. Available scopes listed above.`

## Per-repo incremental update

For each repo being updated:

1. **Check prerequisites.** If `graphs/<repo>/graphify-out/graph.json` does not exist, set result `not built` and skip to the next repo.

2. **Get refs.** Read `graphs/<repo>/.meta.json` to get `old_ref`. Run `git -C upstream/<repo> rev-parse HEAD` to get `current_ref`. If `old_ref == current_ref`, set result `skipped (HEAD unchanged)` and skip.

3. **Run the update.** Before running, read the node count from the existing `graphs/<repo>/graphify-out/graph.json` (call it `old_nodes`).
   - For `scope: full`: run from the repo's graph directory so graphify writes to `graphs/<repo>/graphify-out/`:
     ```
     cd <abs-path>/graphs/<repo> && graphify update <abs-path>/upstream/<repo>
     ```
     `graphify update` re-extracts code files via AST (no LLM calls). Doc/paper/image changes accumulate until the next full rebuild.
   - For `scope: subdirs`: per-subdir graphs live under `graphs/<repo>/<subdir-name>/graphify-out/`. For each subdir path in `graphs/config.json#/repos/<repo>/paths` that has changed files (`git -C upstream/<repo> diff --name-only <old_ref>..<current_ref> -- <subdir-path>`), run:
     ```
     cd <abs-path>/graphs/<repo>/<subdir-name> && graphify update <abs-path>/upstream/<repo>/<subdir-path>
     ```
     Individual subdir graphs are intermediate artifacts and are **not labeled**. After all changed subdirs are re-extracted, re-merge (via the helper that works around the upstream `graphify merge-graphs` bug) and re-cluster the top-level:
     ```
     GRAPHIFY_BIN=$(which graphify); PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//')
     "$PYTHON" .claude/helpers/merge-graphs.py graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json
     graphify cluster-only graphs/<repo>/ --no-viz
     ```
     Then **label the subdir-merged top-level** via the "Community labeling" section of `.claude/commands/bootstrap.md` (subagent batched mode - this scope is large). Subdir name convention (slash → underscore): `server/channels/app` → `server_channels_app`. A full rebuild (replacing per-subdir graphs entirely) only happens when explicitly invoked via `/bootstrap`.
   - For `scope: full`: `graphify update` runs the upstream `--update` incremental pipeline which writes `.graphify_extract.json`, `.graphify_detect.json`, and re-runs clustering internally. After the command completes, **label the per-repo top-level** via the "Community labeling" section of `.claude/commands/bootstrap.md` (host inline mode - these scopes are small). If `graphify update` preserves community IDs and `graphs/<repo>/graphify-out/.graphify_labels.json` already exists with no `Community N` entries, the labels are still valid - skip re-labeling. Otherwise regenerate.

   After the update, read the new node count (call it `new_nodes`); `Δ = new_nodes - old_nodes`.

4. **Update `.meta.json`** with the new `ref` (current HEAD sha) and `built_at` (ISO timestamp).

5. **Result column.** Set to:
   - `updated <Δ> nodes` where `Δ` is the signed delta captured in step 3 (e.g. `updated +12 nodes`, `updated -3 nodes`, `updated 0 nodes`).
   - `skipped (HEAD unchanged)` if step 2 found no change.
   - `not built` if step 1 found no graph.
   - The error message if any step failed (and continue to the next repo).


## Bundle re-merge

For each bundle being processed (either named explicitly or as cascade from a per-repo update):

1. Look up the bundle's `repos` list in `graphs/config.json#/bundles/<bundle-name>`.
2. Collect the `graph.json` paths for every member repo whose `graphs/<repo>/graphify-out/graph.json` exists. If fewer than 2 member graphs exist, set cascade result `skipped (insufficient members: <n>/total)` and skip.
3. Resolve graphify's Python interpreter and call the merge helper (wraps the upstream `graphify merge-graphs` CLI to work around the `MultiGraph` accumulator bug - see `.claude/helpers/merge-graphs.py` docstring):
   ```
   GRAPHIFY_BIN=$(which graphify); PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//')
   "$PYTHON" .claude/helpers/merge-graphs.py <member-graph.json files...> --out graphs/_bundles/<bundle-name>/graphify-out/graph.json
   ```
4. Run: `graphify cluster-only graphs/_bundles/<bundle-name>/ --no-viz` (bundles are typically large; skip HTML render).
5. **Label the bundle** via the "Community labeling" section of `.claude/commands/bootstrap.md` (subagent batched mode). This pass is mandatory - without it, the regenerated `GRAPH_REPORT.md` shows `Community N` placeholders and is unusable as a navigation map.
6. Update `graphs/_bundles/<bundle-name>/.meta.json` with `built_at` (ISO timestamp) and `repos` list.
7. Set result to `merged N nodes` or the error if it failed.


## Cascade logic

When one or more per-repo graphs are updated:

- **Bundles**: read `graphs/config.json#/bundles`. Any bundle whose `repos` list intersects the set of updated repos is cascaded. Perform the bundle re-merge for each such bundle.
- If a cascade step fails, report it inline and continue. Do not abort for one failure.

When a bundle is the explicit target (not a cascade), do not trigger further cascades.


## Output

For per-repo updates, report a Markdown table with columns `Repo | Scope | Old Ref | New Ref | Result`.
- `Old Ref`: first 8 chars of `old_ref` from `.meta.json` (or `—` if missing).
- `New Ref`: first 8 chars of `current_ref`.
- `Result`: as defined in the per-repo steps above.

After the per-repo table (if any), report a second table for cascade/explicit bundle operations with columns `Target | Type | Result`.
- `Type`: `bundle`.
- `Result`: `merged N nodes`, `skipped (<reason>)`, or the error.

If graphify is not installed (`command -v graphify` fails), print: `graphify not installed - install it per README.md then retry.` and stop.


## Notes

- Run each git invocation as a separate Bash tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`. Exception: `cd <graphs/dir> && graphify update <upstream/path>` must stay chained in a single Bash call so graphify writes to the intended CWD.
- Never write inside `upstream/<repo>/`. All output goes to `graphs/`.
- For the no-argument / `--all` mode, parallelize per-repo updates in a single message where the repos are independent. Bundle cascades run after all per-repo updates finish.
