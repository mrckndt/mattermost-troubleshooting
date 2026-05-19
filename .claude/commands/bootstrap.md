---
description: Clone any missing Mattermost repos into upstream/. Idempotent. Optionally triggers a graphify knowledge-graph build with --build-graphs.
argument-hint: [--build-graphs <bundle-name|all|repo-name>  (triggers graphify build)]
---

Apply the Shell conventions from `CLAUDE.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Ensure every repo listed below is cloned under `upstream/<name>/` in the current working directory. For each URL:

1. Derive `<name>` from the last path segment of the URL (e.g. `https://github.com/mattermost/mattermost` -> `mattermost`).
2. If `upstream/<name>/` already exists, skip and report `already present`.
3. Otherwise run `git clone <url> upstream/<name>` and report `cloned` or the error message git printed.

Continue on errors; collect failures and surface them at the end.

Also ensure a `tickets/` directory exists at the working-directory root. If it's missing, create it: `mkdir tickets` (works on macOS / Linux and on Windows cmd / PowerShell). If it already exists, leave it alone - the engineer may have organised it differently and any internal structure is theirs to keep.

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

Report a Markdown table with one row per repo and the columns: `Repo | Result`.
- `Result`: `already present`, `cloned`, or the error message git printed.

## Initial graphify build (optional)

After cloning, optionally trigger the initial knowledge-graph build. This is OFF by default - graph building uses LLM tokens and the user may want to run it in a different session.

Parse `$ARGUMENTS` for a `--build-graphs <selector>` flag. The flag triggers a **graphify knowledge-graph build** (not a code compile / not a build of the upstream repo itself) - it runs `graphify` over the resolved repo set to produce `graphs/<repo>/graphify-out/graph.json` and the cluster artifacts. Valid selectors:
- `<bundle-name>` - graphify-build only the repos listed under `graphs/config.json#/bundles/<bundle-name>/repos`.
- `all` - graphify-build every repo listed in `graphs/config.json#/repos`.
- `<repo>` - graphify-build a single repo (must match a key under `graphs/config.json#/repos`).
- `skip` (or no `--build-graphs` flag) - skip the graphify-build phase entirely; only the clone summary is reported.

If `--build-graphs` is absent, read `graphs/config.json#/bundles` to get the defined bundle names, then prompt the user with those names interpolated as `|`-separated options. For example, with bundles `calls` and `microsoft` defined the prompt is: `Build graphify graphs now? [calls|microsoft|all|skip]`. Wait for the answer. `skip` (or no defined bundles + `skip`) ends the command after the clone summary above.

If a build was requested, do the following in order:

0. **Source `.claude/secrets.env` if present** so Python subprocesses inherit any project-scoped API keys (e.g. `GEMINI_API_KEY` for the fast-path in step 3). If neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` ends up set after sourcing (and after inheriting shell env), print the Gemini tip so the user knows the build will fall back to Claude subagents for semantic extraction:

   ```
   [ -f .claude/secrets.env ] && set -a && . .claude/secrets.env && set +a
   if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
     echo "Couldn't source GEMINI_API_KEY or GOOGLE_API_KEY."
     echo "Tip: set GEMINI_API_KEY or GOOGLE_API_KEY to use Gemini for semantic extraction (pip install 'graphifyy[gemini]')."
     echo "Without it, semantic extraction falls back to Claude subagents (slower and more expensive)."
   fi
   ```

   No-op if `.claude/secrets.env` is absent. Shell init exports (`~/.zshrc`, `~/.zshenv`) inherit automatically.

   **Each Bash tool call is a fresh subshell** - env vars set here do NOT persist to later Bash calls. Every later Bash call that invokes Python with `graphify.llm.extract_corpus_parallel` (step 3 below) must re-source `.claude/secrets.env` in the same call, e.g. prefix the command with `[ -f .claude/secrets.env ] && . .claude/secrets.env;` so the Python child inherits `GEMINI_API_KEY`. (`secrets.env` uses `export` lines, so plain `.` sourcing is sufficient - `set -a` is not required.)

1. **Prereq checks**:
   - `command -v graphify`. If missing, print `graphify CLI not installed - see README.md for install instructions. Skipping graph build.` and stop the build phase (the clone summary above is still the final report).
   - `[ -f graphs/config.json ]`. If missing, print `graphs/config.json not found. Skipping graph build.` and stop.

2. **Resolve build set**: read `graphs/config.json`. For a `<bundle-name>` selector, take `bundles.<bundle-name>.repos` - the list of member repos to process individually. For `all`, take all keys under `repos`. For a single `<repo>`, take just that one. Validate that each repo exists under `upstream/<repo>/`; if not, skip it with a warning row in the report.

3. **For each repo in the build set** (run in parallel via separate Bash tool calls where independent; do not chain with `&&` or pipes):
   - Check `test -f graphs/<repo>/graphify-out/graph.json`. If present, skip with status `already built` (idempotent). The bundle merge file (`graphs/_bundles/<name>/graphify-out/graph.json`) does not satisfy this check - bundle state is independent of member state and is handled in step 4.
   - Resolve `include_types` for this repo: per-repo `repos.<repo>.include_types` if present, else `defaults.include_types`, else all categories. Phase 1 default is `["code", "document"]`.

   **There is no `graphify <path>` bare CLI** - the graphify CLI is subcommand-based (`extract`, `update`, `cluster-only`, `merge-graphs`, etc.). Build a repo by driving the pipeline manually from Python, because the `include_types` filter is applied between `detect` and the extraction stages and no single CLI subcommand does that. Resolve the Python interpreter once from graphify's shebang and reuse it for every Python call:

   ```
   GRAPHIFY_BIN=$(which graphify)
   PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//')
   ```

   **How to invoke Python: inline `-c` or guarded script - never a bare top-level script.** `graphify.extract.extract` spawns worker processes. On macOS, Python uses `spawn` by default; child processes re-import `__main__`. A plain top-level script with no `if __name__ == "__main__":` guard fork-bombs into infinite recursion (you'll see the script's banner printed twice and the run won't return). Two safe shapes:

   - **Inline `python -c "..."`** - simplest for one-shot calls, no guard needed because `__main__` is a string blob the children don't re-execute. Use this for full-scope repos.
   - **Script file with `if __name__ == "__main__":`** - use when you'd otherwise be repeating the same Python across many subdirs (the `mattermost` subdir build). Wrap every body in `def main(): ...` and end the file with `if __name__ == "__main__": main()`.

   **Type quirk:** `graphify.detect.detect()` returns file lists as **strings**, but `graphify.extract.extract()` requires **`Path` objects**. Wrap with `[Path(f) for f in result['files']['code']]` before passing.

   **Working-directory convention:** run the pipeline from inside `BUILD_DIR/`'s parent (`graphs/<repo>/` for full, `graphs/<repo>/<subdir-name>/` for subdir) and pass `cache_root=Path('.')` to `extract()`. That keeps `.graphify_cache/` next to `graphify-out/` and matches what `/graphify-update` expects on re-runs.

   Follow the Shell conventions in `CLAUDE.md` for all CWD/path handling across substeps: use absolute paths (`"$PROJECT_ROOT/..."`) in every `cd`, do not issue a relative `cd graphs/<repo>` more than once (rule 3 in that section explains why it compounds), and `cd "$PROJECT_ROOT"` at the end of each repo's loop iteration before moving on to the next.

   The pipeline for one repo (or one subdir, for subdir-scoped repos):

   1. **Detect.** Set `BUILD_DIR` to `graphs/<repo>/graphify-out/` (full scope) or `graphs/<repo>/<subdir-name>/graphify-out/` (subdir scope, with `<subdir-name>` being the relative path with `/` replaced by `_` - e.g. `server/channels/app` → `server_channels_app`). Set `SRC` to the absolute path of `upstream/<repo>` (full) or `upstream/<repo>/<path>` (subdir). Create `BUILD_DIR`, then from a Python script: `from graphify.detect import detect; result = detect(Path(SRC))`. Zero out every `result['files'][k]` where `k` is not in the resolved `include_types`. Recompute `total_files`. Write the result to `BUILD_DIR/.graphify_detect.json`. Also write `BUILD_DIR/.graphify_root` containing the absolute `SRC` (used by `/graphify-update`).
   2. **AST extract** (code files). From Python: `from graphify.extract import extract`. Build the code-file list as `[Path(f) for f in result['files']['code']]` (note the `Path` wrap - extract() requires it). `cd` into `BUILD_DIR`'s parent first **using an absolute path** (e.g. `cd "$PROJECT_ROOT/graphs/<repo>"`, where `PROJECT_ROOT` was captured before this step). Then call `extract(code_files, cache_root=Path('.'))` and write the returned dict to `BUILD_DIR/.graphify_ast.json`. Do not re-`cd` in later substeps; if a later substep needs a different CWD, use an absolute path.
   3. **Semantic extract** (only if non-code categories survived the `include_types` filter and have files - typically `document` for our config). Skip this step entirely if only `code` is in the allowlist or there are zero non-code files.

      **Backend selection** (matches upstream skill.md Step 3):

      - If `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set in the environment, use the Gemini fast-path:

        ```python
        from graphify.llm import extract_corpus_parallel
        result = extract_corpus_parallel(files, backend="gemini")
        # result is {nodes, edges, hyperedges, input_tokens, output_tokens}
        ```

        Default model is `gemini-3-flash-preview`; allow override via `GRAPHIFY_GEMINI_MODEL`. Write the returned dict to `BUILD_DIR/.graphify_semantic_gemini.json`. The merge substep (step 4) consumes all `.graphify_semantic_*.json` files in the directory; this one plugs in seamlessly.

      - If neither key is set, dispatch parallel general-purpose subagents per ~20-file chunk to read the files and return a `{nodes, edges, hyperedges}` JSON fragment following the SKILL.md schema. Write each chunk under `BUILD_DIR/.graphify_semantic_<N>.json`. The Gemini tip already printed at step 0 if no key was found; do not repeat it here.
   4. **Merge.** From Python: read `.graphify_ast.json` and every `.graphify_semantic_*.json`, concatenate their `nodes` / `edges` / `hyperedges` lists, write to `BUILD_DIR/graph.json`.
   5. **Cluster.** `graphify cluster-only <BUILD_DIR's parent dir> --no-viz` (e.g. `graphify cluster-only graphs/<repo>/ --no-viz` for full scope, or `graphify cluster-only graphs/<repo>/<subdir-name>/ --no-viz` for one subdir). This generates `GRAPH_REPORT.md` and the cluster annotations; the `--no-viz` skips the HTML render.

   - For `scope: full`: run the pipeline once with `BUILD_DIR = graphs/<repo>/graphify-out/` and `SRC = absolute path of upstream/<repo>`. After substep 5, **label the per-repo top-level** via the "Community labeling" section below (using `host inline` mode - this scope is small).
   - For `scope: subdirs`: per-subdir graphs live persistently under `graphs/<repo>/<subdir-name>/graphify-out/`. For each path in `repos.<repo>.paths`, run steps 1-5 with `BUILD_DIR = graphs/<repo>/<subdir-name>/graphify-out/` and `SRC = absolute path of upstream/<repo>/<path>`. **Do not label individual subdir graphs** - they are intermediate artifacts, never pinnable via `/graphify-scope`. After every subdir is built, combine into the top-level graph: `"$PYTHON" .claude/helpers/merge-graphs.py graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json` (helper wraps the upstream `graphify merge-graphs` CLI to work around the `MultiGraph` accumulator bug - see README and `.claude/helpers/merge-graphs.py` docstring), then `graphify cluster-only graphs/<repo>/ --no-viz`, then **label the subdir-merged top-level** via the "Community labeling" section below (using `subagent batched` mode - this scope is large, e.g. ~1076 communities for `mattermost`). Do not delete the per-subdir directories - they are required for incremental updates by `/graphify-update`.

   - Write `graphs/<repo>/.meta.json` with:
     ```
     { "ref": "<git -C \"$PROJECT_ROOT/upstream/<repo>\" rev-parse HEAD>", "built_at": "<ISO timestamp>", "scope": "full|subdirs" }
     ```

4. **Cascade re-merge**: after per-repo builds, for each bundle in `graphs/config.json#/bundles` whose `repos` list is fully built (every member has `graphs/<member>/graphify-out/graph.json`), merge into `graphs/_bundles/<bundle>/graphify-out/graph.json` with `"$PYTHON" .claude/helpers/merge-graphs.py <member graph.json files...> --out graphs/_bundles/<bundle>/graphify-out/graph.json` (helper wraps the upstream `graphify merge-graphs` CLI to work around the `MultiGraph` accumulator bug), then `graphify cluster-only graphs/_bundles/<bundle>/ --no-viz`, then **label the bundle** via the "Community labeling" section below (`subagent batched` mode). Skip bundles with missing members and report them.

5. **Report**: extend the clone summary with a second Markdown table titled `Graph build`, one row per repo in the build set. Columns: `Repo | Status | Nodes | Edges | Time`. Status values: `built`, `already built`, `skipped (<reason>)`, or the error message. Below that table, list the bundles with their final node/edge counts. Do not append destructive-shell rebuild suggestions (e.g. `rm -rf graphs/<repo>`) - if the user wants a rebuild, that's their next call.

Notes for the build phase:
- The graphify CLI has no bare `graphify <path>` form - every call is a subcommand (`extract`, `update`, `cluster-only`, `merge-graphs`, ...). The pipeline above drives it from Python (`graphify.detect.detect`, `graphify.extract.extract`) so the `include_types` filter can be applied between detect and extract; only the `cluster-only` and `merge-graphs` steps shell out to the CLI.
- `graphify extract <path> --out <dir>` exists as a one-shot CLI and is fine for ad-hoc builds with no filter, but the `--include-types` flag does not exist - it is enforced by the Python-driven detect step above.
- `upstream/<repo>/` is read-only. Never write inside it.
- If a single repo build fails, continue with the rest. Collect failures and report at the end. The user can re-run `/bootstrap --build-graphs <repo>` to retry one.

Notes:
- Run each `git clone` as its own Bash tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`. Parallelize across repos in a single message.
- This command does NOT pull or switch. After bootstrap, run `/git-pull` to bring all repos to their latest tracked state (which also cascades graph updates for repos whose HEAD moved), `/git-switch <repo> <ref>` to pin one to a specific tag/branch, or `/graphify-update` to refresh graphs without touching git.
- This file is the canonical list of expected repos. `CLAUDE.md` and `README.md` reference it rather than duplicating the URLs.
- The graph build phase is independent of cloning. `/bootstrap --build-graphs <selector>` can be re-run after cloning to add graphs incrementally.

## Community labeling

Apply this after every `graphify cluster-only` call on a **pinnable** scope: per-repo full-scope graph, per-repo subdir-merged top-level graph, bundle graph. Do NOT apply to individual subdir graphs under `graphs/<repo>/<subdir>/`.

### Why this section exists separately from `cluster-only`

`graphify cluster-only` writes `GRAPH_REPORT.md`, but it leaves community labels as placeholders (`Community 0..N`) and does NOT persist `.graphify_analysis.json`. Upstream skill.md Step 5 (the LLM labeling pass) reads `.graphify_analysis.json` to feed the report regeneration — that file only exists after the full upstream pipeline (skill.md Step 4). For our multi-scope flow (which uses `cluster-only` after merging), we need to **write `.graphify_analysis.json` ourselves**, then run the upstream-style labeling pass against it. The three sub-steps below mirror what upstream's full pipeline does (Step 4 + Step 5), just split across our cluster-then-label boundary.

### Sub-step 1: compute analysis and dump community members

Re-runs `cluster(G)` + `score_all` / `god_nodes` / `surprising_connections` (same calls as `cluster-only` and skill.md Step 4) and writes the result to `.graphify_analysis.json`. Also writes `.graphify_community_members.json` (top 20 member labels per community by degree) for the labeling step. The clustering pass is repeated here because `cluster-only` does not persist its in-memory `communities` dict; the cost is small (Leiden is sub-second on graphs of our typical size).

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

Read `<SCOPE>/graphify-out/.graphify_community_members.json` and produce `<SCOPE>/graphify-out/.graphify_labels.json` as `{ "<cid>": "<2-5 word label>", ... }`. Pick the mode by scale.

**Mode A — host inline** (small scopes: per-repo full-scope graphs with ≤ ~300 communities):

The host Claude reads `.graphify_community_members.json` directly, writes a `{ "<cid>": "<label>", ... }` JSON dict based on the member labels for each community, and saves it to `.graphify_labels.json`. One Bash `Write` tool call.

**Mode B — subagent batched** (large scopes: subdir-merged top-level, bundles — typically hundreds to ~1000+ communities):

The host does not pre-split anything. It decides on a chunk size (30-50 communities), computes how many chunks the total community count needs (`N = ceil(total / chunk_size)`), and dispatches that many subagents in parallel — each one reads the same `.graphify_community_members.json` and labels only its assigned ID range.

1. Dispatch one general-purpose subagent per chunk **in parallel** (all Agent calls in a single message — sequential calls defeat the speedup). Pass each subagent the absolute path to the single shared member dump and its assigned `<start>` and `<end>` community IDs (inclusive-exclusive, like Python slicing).

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

2. After all subagents complete, the host merges every `.graphify_labels_chunk_*.json` into one dict and writes the merged result to `<SCOPE>/graphify-out/.graphify_labels.json`. Helper:

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

After sub-step 3 succeeds, remove the intermediate community-members dump:

```
rm -f <SCOPE>/graphify-out/.graphify_community_members.json
```

`.graphify_analysis.json` and `.graphify_labels.json` are kept on disk so `graphify cluster-only` (and future re-runs of this section) can read them.
