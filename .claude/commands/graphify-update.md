---
description: Incrementally update one or more knowledge graphs. Per-repo runs graphify update; bundle runs merge + re-cluster.
argument-hint: [<repo> | <bundle-name> | --all]
---

Apply the Shell conventions from `CLAUDE.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths). Verify `graphs/` exists; if missing, advise running `/bootstrap` first.

Source `.claude/secrets.env` if present (no-op if absent) so Python subprocesses inherit project-scoped API keys. If neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` is set after sourcing, print the Gemini tip (`graphify update` may run semantic extraction for non-code changes):

```
[ -f .claude/secrets.env ] && set -a && . .claude/secrets.env && set +a
if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
  echo "Couldn't source GEMINI_API_KEY or GOOGLE_API_KEY."
  echo "Tip: set GEMINI_API_KEY or GOOGLE_API_KEY to use Gemini for semantic extraction (pip install 'graphifyy[gemini]')."
  echo "Without it, semantic extraction falls back to Claude subagents (slower and more expensive)."
fi
```

Args: $ARGUMENTS

Parse `$ARGUMENTS` into one of three modes:

- **No argument or `--all`**: update every built per-repo graph, then cascade all bundles.
- **`<repo>`**: matches a key under `graphs/config.json#/repos`. Update that repo's graph, then cascade bundles containing it.
- **`<bundle-name>`**: matches a key under `graphs/config.json#/bundles` and `graphs/_bundles/<bundle-name>/graphify-out/graph.json` exists. Re-merge + re-cluster that bundle only (member repos are assumed current).

If the argument matches none of the above, list all built scopes (`graphs/<repo>/graphify-out/graph.json` and `graphs/_bundles/<bundle>/graphify-out/graph.json`) and stop with: `Target '<arg>' not found. Available scopes listed above.`

## Per-repo incremental update

Follow Shell conventions throughout: absolute paths in every `cd`, `cd "$PROJECT_ROOT"` between repos and before returning.

For each repo being updated:

1. **Check prerequisites.** If `graphs/<repo>/graphify-out/graph.json` does not exist, set result `not built` and skip to the next repo.

2. **Get refs.** Read `graphs/<repo>/.meta.json` to get `old_ref`. Run `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse HEAD` to get `current_ref`. If `old_ref == current_ref`, set result `skipped (HEAD unchanged)` and skip.

3. **Run the update.** Capture `old_nodes` from the existing graph.json first.
   - For `scope: full`:
     ```
     cd <abs-path>/graphs/<repo> && graphify update <abs-path>/upstream/<repo>
     ```
     Re-extracts code via AST (no LLM calls); doc/paper/image changes accumulate until the next full rebuild. After the command, **label the per-repo top-level** via "Community labeling" in `.claude/commands/bootstrap.md` (host inline mode). If `.graphify_labels.json` already exists with no `Community N` entries and community IDs were preserved, skip re-labeling.
   - For `scope: subdirs`: for each subdir in `graphs/config.json#/repos/<repo>/paths` with changed files (`git -C "$PROJECT_ROOT/upstream/<repo>" diff --name-only <old_ref>..<current_ref> -- <subdir-path>`), run:
     ```
     cd <abs-path>/graphs/<repo>/<subdir-name> && graphify update <abs-path>/upstream/<repo>/<subdir-path>
     ```
     Individual subdir graphs are not labeled. After all changed subdirs, re-merge and re-cluster the top-level:
     ```
     GRAPHIFY_BIN=$(which graphify); PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//')
     "$PYTHON" .claude/helpers/merge-graphs.py graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json
     graphify cluster-only graphs/<repo>/ --no-viz
     ```
     Then **label the subdir-merged top-level** (subagent batched mode). Subdir name convention: `/` → `_` (e.g. `server/channels/app` → `server_channels_app`). Full rebuilds only happen via `/bootstrap`.

   After the update, read the new node count (call it `new_nodes`); `Δ = new_nodes - old_nodes`.

4. **Update `.meta.json`** with the new `ref` (current HEAD sha) and `built_at` (ISO timestamp).

5. **Result column.** Set to:
   - `updated <Δ> nodes` where `Δ` is the signed delta captured in step 3 (e.g. `updated +12 nodes`, `updated -3 nodes`, `updated 0 nodes`).
   - `skipped (HEAD unchanged)` if step 2 found no change.
   - `not built` if step 1 found no graph.
   - The error message if any step failed (and continue to the next repo).


## Bundle re-merge

For each bundle being processed (explicit or cascaded):

1. Look up `repos` in `graphs/config.json#/bundles/<bundle-name>`.
2. Collect `graph.json` paths for each member with a built graph. If fewer than 2 exist, set result `skipped (insufficient members: <n>/total)` and skip.
3. Resolve graphify's Python interpreter and call the merge helper (works around the upstream `graphify merge-graphs` `MultiGraph` bug):
   ```
   GRAPHIFY_BIN=$(which graphify); PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//')
   "$PYTHON" .claude/helpers/merge-graphs.py <member-graph.json files...> --out graphs/_bundles/<bundle-name>/graphify-out/graph.json
   ```
4. Run: `graphify cluster-only graphs/_bundles/<bundle-name>/ --no-viz`.
5. **Label the bundle** via "Community labeling" in `.claude/commands/bootstrap.md` (subagent batched mode). Mandatory - without it, `GRAPH_REPORT.md` shows `Community N` placeholders.
6. Update `graphs/_bundles/<bundle-name>/.meta.json` with `built_at` and `repos`.
7. Set result to `merged N nodes` or the error.


## Cascade logic

After per-repo updates: read `graphs/config.json#/bundles`; cascade any bundle whose `repos` list intersects the updated set. If a cascade step fails, report it inline and continue. When a bundle is the explicit target, do not trigger further cascades.


## Output

Per-repo: Markdown table `Repo | Scope | Old Ref | New Ref | Result`.
- `Old Ref`: first 8 chars from `.meta.json` (or `—` if missing). `New Ref`: first 8 chars of current HEAD.
- `Result`: as defined in the steps above.

After the per-repo table, a second table for bundles: `Target | Type | Result` (`Type` = `bundle`; `Result` = `merged N nodes`, `skipped (<reason>)`, or error).

If graphify is not installed, print: `graphify not installed - install it per README.md then retry.` and stop.


## Notes

- Run each git invocation as a separate Bash tool call; do not chain or append `2>&1`. Exception: `cd <graphs/dir> && graphify update <upstream/path>` must stay chained so graphify writes to the correct CWD.
- Never write inside `upstream/<repo>/`. All output goes to `graphs/`.
- For `--all`, parallelize per-repo updates in a single message. Bundle cascades run after all per-repo updates finish.
