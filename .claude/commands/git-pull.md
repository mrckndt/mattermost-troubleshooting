---
description: Run git pull --ff-only on the current branch of one repo (arg) or every repo under upstream/ (no arg)
argument-hint: [<repo>]
---

Apply the Shell conventions from `CLAUDE.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Source `.claude/secrets.env` if present (no-op if absent). If neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` is set after sourcing, print the Gemini tip (the cascade calls `graphify update`, which may run semantic extraction):

```
[ -f .claude/secrets.env ] && set -a && . .claude/secrets.env && set +a
if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
  echo "Couldn't source GEMINI_API_KEY or GOOGLE_API_KEY."
  echo "Tip: set GEMINI_API_KEY or GOOGLE_API_KEY to use Gemini for semantic extraction (pip install 'graphifyy[gemini]')."
  echo "Without it, semantic extraction falls back to Claude subagents (slower and more expensive)."
fi
```

Args: optionally a single `<repo>` name matching a directory under `upstream/`.

- If an argument is given: verify `upstream/<repo>/` exists (if not, list available repos and stop). Process that repo only.
- If no argument: process every repo under `upstream/`.

For each repo:

1. `git -C "$PROJECT_ROOT/upstream/<repo>" pull --ff-only`. Report whatever git says; do not pre-check or guard.
2. `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD` to capture the branch (`HEAD` = detached, report as `(detached)`).
3. Continue on error.

Report a Markdown table: `Repo | Branch | Pull | Graph | Cascade`.
- `Pull`: `up to date`, `updated <oldsha>..<newsha>`, or the git error.
- `Graph` / `Cascade`: see "Graphify update cascade" below. Leave both blank if graphify is not installed.

After processing, mark each repo as fetched-this-session so the lazy-fetch policy in `CLAUDE.md` skips it later.

## Graphify update cascade

Run only if `command -v graphify` succeeds AND `graphs/config.json` exists. Otherwise leave `Graph` and `Cascade` blank (do not fail the pull).

For each repo where `Pull` = `updated <oldsha>..<newsha>`:

1. If `graphs/<repo>/graphify-out/graph.json` does not exist: `Graph = n/a (not built)`, `Cascade = none`. Skip.
2. Capture `old_nodes`, then update per scope:
   - For `scope: full`: `cd <abs-path>/graphs/<repo> && graphify update <abs-path>/upstream/<repo>` (chained; re-extracts code via AST, no LLM calls). After the update, **label the per-repo top-level** via "Community labeling" in `.claude/commands/bootstrap.md` (host inline mode). Skip re-labeling if `.graphify_labels.json` exists with no `Community N` entries and community IDs were preserved.
   - For `scope: subdirs`: for each subdir with changed files (`git -C "$PROJECT_ROOT/upstream/<repo>" diff --name-only <oldsha>..<newsha> -- <subdir-path>`), run `cd <abs-path>/graphs/<repo>/<subdir-name> && graphify update <abs-path>/upstream/<repo>/<subdir-path>` (`<subdir-name>` = path with `/` → `_`). Individual subdir graphs are not labeled. After all changed subdirs, re-merge and re-cluster: `GRAPHIFY_BIN=$(which graphify); PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//'); "$PYTHON" .claude/helpers/merge-graphs.py graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json`, then `graphify cluster-only graphs/<repo>/ --no-viz`, then **label the subdir-merged top-level** (subagent batched mode).
   - Update `.meta.json` with the new HEAD sha and ISO timestamp.
   - Set `Graph = updated <Δ> nodes` (signed delta).
3. If `Pull = up to date` and the graph exists: `Graph = skipped (unchanged)`.
4. If `Pull` errored: `Graph = skipped (pull failed)`.

After per-repo updates:

5. **Bundles**: any bundle whose `repos` list includes a repo rebuilt in step 2 is cascaded. For each fully-built affected bundle: re-merge via the helper (`GRAPHIFY_BIN=$(which graphify); PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//'); "$PYTHON" .claude/helpers/merge-graphs.py <member graph.json files> --out graphs/_bundles/<bundle>/graphify-out/graph.json`), then `graphify cluster-only graphs/_bundles/<bundle>/ --no-viz`, then **label the bundle** (subagent batched mode).
6. Set `Cascade` to a comma-separated list of bundles that re-merged. Rows with `skipped (unchanged|pull failed)` or `n/a (not built)` get `Cascade = none`.

If a cascade step fails, report it inline in the `Cascade` column and continue.

Notes:
- Run each git invocation as a separate Bash tool call; do not chain or append `2>&1`. Parallelize across repos in a single message. Exception: `cd <graphs/dir> && graphify update <upstream/path>` must stay chained.
- This command does NOT refresh tags. For new tags before `/git-switch`, run `git -C "$PROJECT_ROOT/upstream/<repo>" fetch --tags` first.
- The graphify update is best-effort: if it fails, the pull is still successful; the `Graph` column captures the reason.
