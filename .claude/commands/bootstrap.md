---
description: Clone any missing Mattermost repos into upstream/. Idempotent. Optionally triggers a graphify knowledge-graph build with --build-graphs.
argument-hint: [--build-graphs <bundle-name|all|repo-name>  (triggers graphify build)]
---

Apply the Shell conventions from `CLAUDE.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Clone every repo listed below under `upstream/<name>/`. For each URL:

1. Derive `<name>` from the last path segment of the URL.
2. If `upstream/<name>/` already exists, skip and report `already present`.
3. Otherwise run `git clone <url> upstream/<name>` and report `cloned` or the git error.

Continue on errors; collect failures and surface them at the end.

Also ensure `tickets/` exists at the working-directory root. If missing, `mkdir tickets`. If present, leave it alone.

Repos to bootstrap (alphabetical):

- `https://github.com/mattermost/calls-offloader`
- `https://github.com/mattermost/calls-recorder`
- `https://github.com/mattermost/calls-transcriber`
- `https://github.com/mattermost/desktop`
- `https://github.com/mattermost/docker`
- `https://github.com/mattermost/docs`
- `https://github.com/mattermost/mattermost`
- `https://github.com/mattermost/mattermost-developer-documentation`
- `https://github.com/mattermost/mattermost-helm`
- `https://github.com/mattermost/mattermost-mobile`
- `https://github.com/mattermost/mattermost-operator`
- `https://github.com/mattermost/mattermost-plugin-agents`
- `https://github.com/mattermost/mattermost-plugin-boards`
- `https://github.com/mattermost/mattermost-plugin-calls`
- `https://github.com/mattermost/mattermost-plugin-channel-automation`
- `https://github.com/mattermost/mattermost-plugin-github`
- `https://github.com/mattermost/mattermost-plugin-gitlab`
- `https://github.com/mattermost/mattermost-plugin-google-calendar`
- `https://github.com/mattermost/mattermost-plugin-jira`
- `https://github.com/mattermost/mattermost-plugin-mscalendar`
- `https://github.com/mattermost/mattermost-plugin-msteams`
- `https://github.com/mattermost/mattermost-plugin-msteams-meetings`
- `https://github.com/mattermost/mattermost-plugin-playbooks`
- `https://github.com/mattermost/mattermost-plugin-zoom`
- `https://github.com/mattermost/migration-assist`
- `https://github.com/mattermost/rtcd`

Report a Markdown table: `Repo | Result`, where `Result` is `already present`, `cloned`, or the git error.

## Initial graphify build (optional)

Graph building is OFF by default (uses LLM tokens). Parse `$ARGUMENTS` for `--build-graphs <selector>`. Valid selectors:
- `<bundle-name>` - build the repos listed under `graphs/config.json#/bundles/<bundle-name>/repos`.
- `all` - build every repo in `graphs/config.json#/repos`.
- `<repo>` - build a single repo (must match a key under `graphs/config.json#/repos`).
- `skip` (or flag absent) - skip the build phase; only the clone summary is reported.

If `--build-graphs` is absent, read `graphs/config.json#/bundles`, then prompt: `Build graphify graphs now? [<bundle1>|<bundle2>|all|skip]`. Wait for the answer. `skip` (or no bundles defined) ends here.

If a build was requested, proceed in order:

0. **Source `.claude/secrets.env` if present** so Python subprocesses inherit project-scoped API keys. If neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` is set after sourcing, print the Gemini tip:

   ```
   [ -f .claude/secrets.env ] && set -a && . .claude/secrets.env && set +a
   if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
     echo "Couldn't source GEMINI_API_KEY or GOOGLE_API_KEY."
     echo "Tip: set GEMINI_API_KEY or GOOGLE_API_KEY to use Gemini for semantic extraction (pip install 'graphifyy[gemini]')."
     echo "Without it, semantic extraction falls back to Claude subagents (slower and more expensive)."
   fi
   ```

   No-op if `.claude/secrets.env` is absent. Each Bash tool call is a fresh subshell - env vars do not persist. Every Bash call that invokes `graphify.llm.extract_corpus_parallel` (step 3) must re-source `.claude/secrets.env` in the same call: `[ -f .claude/secrets.env ] && . .claude/secrets.env;`. (`secrets.env` uses `export` lines, so plain `.` sourcing is sufficient.)

1. **Prereq checks**: `command -v graphify` (if missing, print `graphify CLI not installed - see README.md for install instructions. Skipping graph build.` and stop) and `[ -f graphs/config.json ]` (if missing, print `graphs/config.json not found. Skipping graph build.` and stop). The clone summary is still the final report.

2. **Resolve build set**: read `graphs/config.json`. For `<bundle-name>`, take `bundles.<bundle-name>.repos`. For `all`, take all keys under `repos`. For `<repo>`, take just that one. Skip any repo not present under `upstream/<repo>/` with a warning row in the report.

3. **For each repo in the build set** (parallel Bash tool calls where independent; do not chain with `&&` or pipes):
   - If `graphs/<repo>/graphify-out/graph.json` exists, skip with status `already built` (idempotent). Bundle state is independent and is handled in step 4.
   - Resolve `include_types`: `repos.<repo>.include_types` if present, else `defaults.include_types`, else all categories. Phase 1 default is `["code", "document"]`.

   **No bare `graphify <path>` CLI** - graphify is subcommand-based (`extract`, `update`, `cluster-only`, `merge-graphs`, etc.). Drive the pipeline from Python because `include_types` must be applied between `detect` and extraction, and no single subcommand does that. Resolve the Python interpreter once from graphify's shebang:

   ```
   GRAPHIFY_BIN=$(which graphify)
   PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//')
   ```

   **Python invocation: inline `-c` or guarded script, never bare top-level.** `graphify.extract.extract` spawns workers; on macOS (spawn default), child processes re-import `__main__`. A bare top-level script with no `if __name__ == "__main__":` guard fork-bombs. Two safe forms:

   - **Inline `python -c "..."`** - no guard needed (children don't re-execute a string blob). Use for full-scope repos.
   - **Script file with `if __name__ == "__main__":`** - use when repeating the same Python across many subdirs (e.g. the `mattermost` subdir build). Wrap the body in `def main()` and call it under the guard.

   **Type quirk:** `detect()` returns file lists as strings; `extract()` requires `Path` objects. Wrap: `[Path(f) for f in result['files']['code']]`.

   **CWD convention:** run the pipeline from `BUILD_DIR`'s parent and pass `cache_root=Path('.')` to `extract()`, keeping `.graphify_cache/` next to `graphify-out/` as `/graphify-update` expects.

   Follow Shell conventions in `CLAUDE.md`: absolute paths in every `cd`, no repeated relative `cd graphs/<repo>` (it compounds), `cd "$PROJECT_ROOT"` at the end of each loop iteration.

   The pipeline for one repo (or subdir):

   1. **Detect.** Set `BUILD_DIR` to `graphs/<repo>/graphify-out/` (full) or `graphs/<repo>/<subdir-name>/graphify-out/` (subdir; `<subdir-name>` = subdir path with `/` → `_`, e.g. `server/channels/app` → `server_channels_app`). Set `SRC` to the absolute path of `upstream/<repo>` (full) or `upstream/<repo>/<path>` (subdir). Create `BUILD_DIR`, then detect: `from graphify.detect import detect; result = detect(Path(SRC))`. Zero out `result['files'][k]` for every `k` not in `include_types`; recompute `total_files`. Write `BUILD_DIR/.graphify_detect.json` and `BUILD_DIR/.graphify_root` (absolute `SRC`, used by `/graphify-update`).
   2. **AST extract** (code files). `cd` to `BUILD_DIR`'s parent using an absolute path, then call `extract([Path(f) for f in result['files']['code']], cache_root=Path('.'))` and write the result to `BUILD_DIR/.graphify_ast.json`. Do not re-`cd` in later substeps; use absolute paths if a different CWD is needed.
   3. **Semantic extract** (non-code categories that survived `include_types` and have files, typically `document`). Skip if only `code` is in the allowlist or there are no non-code files.

      **Backend selection:**

      - If `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set, use the Gemini fast-path:

        ```python
        from graphify.llm import extract_corpus_parallel
        result = extract_corpus_parallel(files, backend="gemini")
        # result is {nodes, edges, hyperedges, input_tokens, output_tokens}
        ```

        Default model is `gemini-3-flash-preview`; override via `GRAPHIFY_GEMINI_MODEL`. Write the result to `BUILD_DIR/.graphify_semantic_gemini.json`. The merge step (step 4) consumes all `.graphify_semantic_*.json` files.

      - If neither key is set, dispatch parallel subagents per ~20-file chunk to return a `{nodes, edges, hyperedges}` JSON fragment per the SKILL.md schema. Write each chunk to `BUILD_DIR/.graphify_semantic_<N>.json`. Do not repeat the Gemini tip here.
   4. **Merge.** Read `.graphify_ast.json` and every `.graphify_semantic_*.json`; concatenate `nodes` / `edges` / `hyperedges`; write to `BUILD_DIR/graph.json`.
   5. **Cluster.** `graphify cluster-only <BUILD_DIR's parent> --no-viz`. Generates `GRAPH_REPORT.md` and cluster annotations; `--no-viz` skips the HTML render.

   - For `scope: full`: run the pipeline once (`BUILD_DIR = graphs/<repo>/graphify-out/`, `SRC = upstream/<repo>` absolute path). After substep 5, **label the per-repo top-level** via the "Community labeling" section below (host inline mode).
   - For `scope: subdirs`: per-subdir graphs live under `graphs/<repo>/<subdir-name>/graphify-out/`. For each path in `repos.<repo>.paths`, run steps 1-5 (`BUILD_DIR = graphs/<repo>/<subdir-name>/graphify-out/`, `SRC = upstream/<repo>/<path>` absolute). **Do not label individual subdir graphs** - they are intermediate artifacts. After all subdirs are built, merge into the top-level: `"$PYTHON" .claude/helpers/merge-graphs.py graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json` (helper works around the upstream `graphify merge-graphs` `MultiGraph` bug), then `graphify cluster-only graphs/<repo>/ --no-viz`, then **label the subdir-merged top-level** (subagent batched mode). Do not delete per-subdir directories - `/graphify-update` requires them.

   - Write `graphs/<repo>/.meta.json` with:
     ```
     { "ref": "<git -C \"$PROJECT_ROOT/upstream/<repo>\" rev-parse HEAD>", "built_at": "<ISO timestamp>", "scope": "full|subdirs" }
     ```

4. **Cascade re-merge**: for each bundle in `graphs/config.json#/bundles` whose every member has `graphs/<member>/graphify-out/graph.json`, merge: `"$PYTHON" .claude/helpers/merge-graphs.py <member graph.json files...> --out graphs/_bundles/<bundle>/graphify-out/graph.json`, then `graphify cluster-only graphs/_bundles/<bundle>/ --no-viz`, then **label the bundle** (subagent batched mode). Skip and report bundles with missing members.

5. **Report**: add a second Markdown table (`Graph build`) with columns `Repo | Status | Nodes | Edges | Time`. Status: `built`, `already built`, `skipped (<reason>)`, or the error. Below it, list bundles with final node/edge counts. Do not suggest `rm -rf graphs/<repo>` rebuilds - that is the user's call.

Notes for the build phase:
- The graphify CLI has no bare `graphify <path>` form. The pipeline drives it from Python so `include_types` can be applied between detect and extract; only `cluster-only` and `merge-graphs` shell out to the CLI.
- `graphify extract <path> --out <dir>` exists as a one-shot CLI but has no `--include-types` flag; use the Python-driven detect step to enforce the filter.
- `upstream/<repo>/` is read-only. Never write inside it.
- If one repo fails, continue and report at the end. Retry with `/bootstrap --build-graphs <repo>`.

Notes:
- Run each `git clone` as its own Bash tool call; do not chain or append `2>&1`. Parallelize across repos in a single message.
- This command does NOT pull or switch. Use `/git-pull` (pulls + cascades graph updates), `/git-switch <repo> <ref>` (pin to tag/branch), or `/graphify-update` (refresh graphs without touching git).
- This file is the canonical repo list. `CLAUDE.md` and `README.md` reference it rather than duplicating URLs.
- The graph build phase is independent of cloning; re-run `/bootstrap --build-graphs <selector>` to add graphs incrementally.

## Community labeling

Apply after every `graphify cluster-only` on a **top-level** scope (per-repo full, per-repo subdir-merged, bundle). Do NOT apply to individual subdir graphs under `graphs/<repo>/<subdir>/`.

### Why this section exists separately from `cluster-only`

`graphify cluster-only` writes `GRAPH_REPORT.md` but leaves community labels as placeholders (`Community 0..N`) and does not persist `.graphify_analysis.json`. For our multi-scope flow we must write `.graphify_analysis.json` ourselves, then run the LLM labeling pass against it. The three sub-steps below mirror upstream's pipeline (Step 4 + Step 5) across our cluster-then-label boundary.

### Sub-step 1: compute analysis and dump community members

Re-runs `cluster(G)` + `score_all` / `god_nodes` / `surprising_connections` and writes `.graphify_analysis.json`. Also writes `.graphify_community_members.json` (top 20 members per community by degree). The clustering re-run is necessary because `cluster-only` does not persist its `communities` dict; the cost is small (Leiden is sub-second at our graph sizes).

```
$(cat <SCOPE>/graphify-out/.graphify_python 2>/dev/null || which graphify | xargs -I{} head -1 {} | sed 's/^#!//') -c "
import json
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions

scope = '<SCOPE>'
out = Path(f'{scope}/graphify-out')

g_data = json.loads((out / 'graph.json').read_text(encoding='utf-8'))
directed = bool(g_data.get('directed', False))
G = build_from_json(g_data, directed=directed)

communities = cluster(G)
cohesion = score_all(G, communities)
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
placeholder_labels = {cid: f'Community {cid}' for cid in communities}
questions = suggest_questions(G, communities, placeholder_labels)

analysis = {
    'communities': {str(k): v for k, v in communities.items()},
    'cohesion': {str(k): v for k, v in cohesion.items()},
    'gods': gods,
    'surprises': surprises,
    'questions': questions,
}
(out / '.graphify_analysis.json').write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding='utf-8')

# Per-community member dump for label generation (top 20 by degree).
members = {}
for cid, node_ids in communities.items():
    scored = sorted(node_ids, key=lambda n: -G.degree(n))[:20]
    members[str(cid)] = [G.nodes[n].get('label', n) for n in scored]
(out / '.graphify_community_members.json').write_text(json.dumps(members, ensure_ascii=False), encoding='utf-8')
print(f'Analysis written: {len(communities)} communities, {sum(len(v) for v in communities.values())} clustered nodes')
"
```

### Sub-step 2: generate labels (two modes)

Read `.graphify_community_members.json` and produce `.graphify_labels.json` as `{ "<cid>": "<2-5 word label>", ... }`. Pick mode by scale.

**Mode A — host inline** (small: per-repo full-scope graphs with ≤ ~300 communities): the host reads the member dump, writes a `{ "<cid>": "<label>", ... }` dict, and saves it to `.graphify_labels.json` in one Write tool call.

**Mode B — subagent batched** (large: subdir-merged top-level, bundles, typically hundreds to ~1000+ communities): choose a chunk size of 30-50 communities, compute `N = ceil(total / chunk_size)`, dispatch that many subagents in parallel (all Agent calls in one message; sequential calls defeat the speedup). Each subagent reads the same `.graphify_community_members.json` and labels its assigned ID range.

1. Dispatch one subagent per chunk in parallel with the absolute path to the member dump and its `<start>` / `<end>` IDs (inclusive-exclusive).

   Subagent prompt template:
   ```
   You are labeling knowledge graph communities.

   Read this file:
     <ABSOLUTE-PATH>/<SCOPE>/graphify-out/.graphify_community_members.json

   It is a JSON dict { "<community_id>": [<up to 20 node labels>] } covering every community in the scope.

   You are responsible for community IDs <start> through <end-1> only. Filter to that range; do not label communities outside it.

   For each community ID in your range, pick a 2-5 word plain-language name that captures what the member nodes have in common. If a community looks incoherent (no clear theme), use a descriptive fallback like "Misc utilities" or "Test helpers" - never leave it as "Community N".

   Output ONLY a JSON dict { "<cid>": "<label>", ... } covering exactly the IDs in your range. No explanation, no markdown fences.

   Write the JSON via the Write tool to this exact absolute path:
     <ABSOLUTE-PATH>/<SCOPE>/graphify-out/.graphify_labels_chunk_<N>.json
   ```

2. After all subagents complete, merge every `.graphify_labels_chunk_*.json` into one dict and write to `.graphify_labels.json`. Helper:

   ```
   $(cat <SCOPE>/graphify-out/.graphify_python 2>/dev/null || which graphify | xargs -I{} head -1 {} | sed 's/^#!//') -c "
   import json, glob
   from pathlib import Path

   scope = '<SCOPE>'
   out = Path(f'{scope}/graphify-out')
   merged = {}
   for c in sorted(glob.glob(str(out / '.graphify_labels_chunk_*.json'))):
       merged.update(json.loads(Path(c).read_text(encoding='utf-8')))
   (out / '.graphify_labels.json').write_text(json.dumps(merged, ensure_ascii=False), encoding='utf-8')
   for c in glob.glob(str(out / '.graphify_labels_chunk_*.json')):
       Path(c).unlink()
   print(f'Merged {len(merged)} labels')
   "
   ```

### Sub-step 3: regenerate the report with real labels

```
$(cat <SCOPE>/graphify-out/.graphify_python 2>/dev/null || which graphify | xargs -I{} head -1 {} | sed 's/^#!//') -c "
import json
from pathlib import Path
from graphify.build import build_from_json
from graphify.analyze import suggest_questions
from graphify.report import generate

scope = '<SCOPE>'
out = Path(f'{scope}/graphify-out')

g_data = json.loads((out / 'graph.json').read_text(encoding='utf-8'))
directed = bool(g_data.get('directed', False))
G = build_from_json(g_data, directed=directed)

analysis = json.loads((out / '.graphify_analysis.json').read_text(encoding='utf-8'))
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
labels = {int(k): v for k, v in json.loads((out / '.graphify_labels.json').read_text(encoding='utf-8')).items()}

# Regenerate questions with real labels (questions depend on labels).
questions = suggest_questions(G, communities, labels)

# Read tokens/detection if the full-pipeline intermediates are present (full per-repo builds);
# otherwise use stubs (bundle re-merges, subdir-merged top-level).
extract_path = out / '.graphify_extract.json'
detect_path = out / '.graphify_detect.json'
if extract_path.exists() and detect_path.exists():
    extraction = json.loads(extract_path.read_text(encoding='utf-8'))
    detection = json.loads(detect_path.read_text(encoding='utf-8'))
    tokens = {'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}
else:
    detection = {'total_files': 0, 'total_words': 0, 'files': {}}
    tokens = {'input': 0, 'output': 0}

report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, scope, suggested_questions=questions)
(out / 'GRAPH_REPORT.md').write_text(report, encoding='utf-8')
print(f'Report regenerated: {len(communities)} communities labeled')
"
```

### Cleanup

After sub-step 3 succeeds, remove the intermediate member dump:

```
rm -f <SCOPE>/graphify-out/.graphify_community_members.json
```

Keep `.graphify_analysis.json` and `.graphify_labels.json` on disk for future re-runs.
