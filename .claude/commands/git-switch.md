---
description: Switch a cloned repo under upstream/ to a tag or branch (no ref = default branch)
argument-hint: <repo> [<ref>]
---

Apply the Shell conventions from `CLAUDE.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Source `.claude/secrets.env` if present (no-op if absent). If neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` is set after sourcing, print the Gemini tip (the post-switch cascade calls `graphify update`, which may run semantic extraction):

```
[ -f .claude/secrets.env ] && set -a && . .claude/secrets.env && set +a
if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
  echo "Couldn't source GEMINI_API_KEY or GOOGLE_API_KEY."
  echo "Tip: set GEMINI_API_KEY or GOOGLE_API_KEY to use Gemini for semantic extraction (pip install 'graphifyy[gemini]')."
  echo "Without it, semantic extraction falls back to Claude subagents (slower and more expensive)."
fi
```

Args: $ARGUMENTS

Parse args as `<repo> [<ref>]`. Switch `upstream/<repo>` to `<ref>`, or the default branch if `<ref>` is omitted.

Steps:

1. Verify `upstream/<repo>/` exists; if not, list available repos and stop.
2. `git -C "$PROJECT_ROOT/upstream/<repo>" status -s`. If non-empty, refuse and report the changes (commit, stash, or discard before retrying).
3. Switch (no upfront fetch; fetch only as fallback):
   - If `<ref>` is empty: resolve the default branch via `git -C "$PROJECT_ROOT/upstream/<repo>" symbolic-ref refs/remotes/origin/HEAD --short` (strip `origin/` prefix), then `git switch <default>`.
   - Otherwise: (a) `git switch <ref>`; (b) if that fails, `git switch --detach <ref>`; (c) if both fail, `fetch --tags --prune` once then repeat (a) and (b). Do not pre-check whether the ref is a tag.
4. Report by reformatting `git switch`'s own output with the repo path prepended. Prefix `Switched upstream/<repo> to ...`, preserving the rest verbatim. Examples:
   - `Switched to branch 'master'` → `Switched upstream/mattermost to branch 'master'`.
   - `Switched to a new branch 'release-11.5'` → `Switched upstream/mattermost to a new branch 'release-11.5'`.
   - For a detached tag (`HEAD is now at <sha> ...`): `Switched upstream/<repo> to detached HEAD on tag 'v10.5.1' (<sha>)`.
   Do NOT call `describe --tags --always` or any other extra git command.

5. **Graphify post-switch update.** Run only if `command -v graphify` succeeds AND `graphs/config.json` exists AND `graphs/<repo>/graphify-out/graph.json` exists. Otherwise append `Graph: skipped (<reason>).` and continue.
   - Read the pre-switch ref from `graphs/<repo>/.meta.json`. If it equals the new HEAD sha, set `Graph: skipped (HEAD unchanged)` and stop.
   - Capture `old_nodes`, then update per scope:
     - For `scope: full`: `cd <abs-path>/graphs/<repo> && graphify update <abs-path>/upstream/<repo>` (chained; AST re-extract, no LLM calls). After the update, **label the per-repo top-level** via "Community labeling" in `.claude/commands/bootstrap.md` (host inline mode). Skip re-labeling if `.graphify_labels.json` exists with no `Community N` entries and community IDs were preserved.
     - For `scope: subdirs`: for each subdir with changed files (`git -C "$PROJECT_ROOT/upstream/<repo>" diff --name-only <old-ref>..HEAD -- <subdir-path>`), run `cd <abs-path>/graphs/<repo>/<subdir-name> && graphify update <abs-path>/upstream/<repo>/<subdir-path>` (`<subdir-name>` = path with `/` → `_`). Individual subdir graphs not labeled. After all changed subdirs, re-merge and re-cluster: `GRAPHIFY_BIN=$(which graphify); PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//'); "$PYTHON" .claude/helpers/merge-graphs.py graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json`, then `graphify cluster-only graphs/<repo>/ --no-viz`, then **label the subdir-merged top-level** (subagent batched mode).
   - Update `.meta.json` with the new ref and ISO timestamp.
   - Set `Δ = new_nodes - old_nodes`.
   - **Cascade**: for every bundle whose `repos` list contains this repo and whose member set is fully built, re-merge (`"$PYTHON" .claude/helpers/merge-graphs.py <member graph.json files> --out graphs/_bundles/<bundle>/graphify-out/graph.json`), then `graphify cluster-only graphs/_bundles/<bundle>/ --no-viz`, then **label the bundle** (subagent batched mode).
   - Append: `Graph: updated <Δ> nodes. Cascade: <comma-separated bundles|none>.`
   - On failure, surface it on the same line and continue. Do not abort for a graphify failure.

Do NOT auto-revert at the end of the turn. Leave the repo on the chosen ref for follow-up reads.
