---
description: Clone any missing Mattermost repos into upstream/. Idempotent - skips repos already present.
argument-hint: [--build <bundle-name|all|repo-name>]
---

First verify the shell is at the project root - a prior skill/tool may have left it in a subdirectory, silently misrouting relative paths like `upstream/<name>`. Run `pwd && ls -1 CLAUDE.md README.md .gitignore .claude claude-md upstream`. If `pwd` doesn't end in `/mattermost-troubleshooting` or any entry is missing, `cd` (absolute path) to the root before continuing.

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

Parse `$ARGUMENTS` for a `--build <selector>` flag. Valid selectors:
- `<bundle-name>` - build only the repos listed under `graphs/config.json#/bundles/<bundle-name>/repos`.
- `all` - build every repo listed in `graphs/config.json#/repos`.
- `<repo>` - build a single repo (must match a key under `graphs/config.json#/repos`).
- `skip` (or no `--build` flag) - skip the build phase entirely.

If `--build` is absent, read `graphs/config.json#/bundles` to get the defined bundle names, then prompt the user with those names interpolated as `|`-separated options. For example, with bundles `calls` and `microsoft` defined the prompt is: `Build graphify graphs now? [calls|microsoft|all|skip]`. Wait for the answer. `skip` (or no defined bundles + `skip`) ends the command after the clone summary above.

If a build was requested, do the following in order:

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

   The pipeline for one repo (or one subdir, for subdir-scoped repos):

   1. **Detect.** Set `BUILD_DIR` to `graphs/<repo>/graphify-out/` (full scope) or `graphs/<repo>/<subdir-name>/graphify-out/` (subdir scope, with `<subdir-name>` being the relative path with `/` replaced by `_` - e.g. `server/channels/app` → `server_channels_app`). Set `SRC` to the absolute path of `upstream/<repo>` (full) or `upstream/<repo>/<path>` (subdir). Create `BUILD_DIR`, then from a Python script: `from graphify.detect import detect; result = detect(Path(SRC))`. Zero out every `result['files'][k]` where `k` is not in the resolved `include_types`. Recompute `total_files`. Write the result to `BUILD_DIR/.graphify_detect.json`. Also write `BUILD_DIR/.graphify_root` containing the absolute `SRC` (used by `/graphify-update`).
   2. **AST extract** (code files). From Python: `from graphify.extract import collect_files, extract`. Build the code-file list from `result['files']['code']`. Call `extract(code_files, cache_root=Path(BUILD_DIR).parent)` and write the returned dict to `BUILD_DIR/.graphify_ast.json`.
   3. **Semantic extract** (only if non-code categories survived the `include_types` filter and have files - typically `document` for our config). Dispatch parallel general-purpose subagents per ~20-file chunk to read the files and return a `{nodes, edges, hyperedges}` JSON fragment following the SKILL.md schema. Write each chunk under `BUILD_DIR/.graphify_semantic_<N>.json`. Skip this step entirely if only `code` is in the allowlist or there are zero non-code files.
   4. **Merge.** From Python: read `.graphify_ast.json` and every `.graphify_semantic_*.json`, concatenate their `nodes` / `edges` / `hyperedges` lists, write to `BUILD_DIR/graph.json`.
   5. **Cluster.** `graphify cluster-only <BUILD_DIR's parent dir> --no-viz` (e.g. `graphify cluster-only graphs/<repo>/ --no-viz` for full scope, or `graphify cluster-only graphs/<repo>/<subdir-name>/ --no-viz` for one subdir). This generates `GRAPH_REPORT.md` and the cluster annotations; the `--no-viz` skips the HTML render.

   - For `scope: full`: run the pipeline once with `BUILD_DIR = graphs/<repo>/graphify-out/` and `SRC = absolute path of upstream/<repo>`.
   - For `scope: subdirs`: per-subdir graphs live persistently under `graphs/<repo>/<subdir-name>/graphify-out/`. For each path in `repos.<repo>.paths`, run steps 1-5 with `BUILD_DIR = graphs/<repo>/<subdir-name>/graphify-out/` and `SRC = absolute path of upstream/<repo>/<path>`. After every subdir is built, combine into the top-level graph: `graphify merge-graphs graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json`, then `graphify cluster-only graphs/<repo>/ --no-viz`. Do not delete the per-subdir directories - they are required for incremental updates by `/graphify-update`.

   - Write `graphs/<repo>/.meta.json` with:
     ```
     { "ref": "<git -C upstream/<repo> rev-parse HEAD>", "built_at": "<ISO timestamp>", "scope": "full|subdirs" }
     ```

4. **Cascade re-merge**: after per-repo builds, for each bundle in `graphs/config.json#/bundles` whose `repos` list is fully built (every member has `graphs/<member>/graphify-out/graph.json`), merge into `graphs/_bundles/<bundle>/graphify-out/graph.json` with `graphify merge-graphs`, then `graphify cluster-only graphs/_bundles/<bundle>/ --no-viz`. Skip bundles with missing members and report them.

5. **`_all` graph**: merge every existing per-repo `graph.json` into `graphs/_all/graphify-out/graph.json`, then `graphify cluster-only graphs/_all/ --no-viz`. (The user can pin `_all` via `/graphify-scope _all` for cross-cutting questions.)

6. **Report**: extend the clone summary with a second Markdown table titled `Graph build`, one row per repo in the build set. Columns: `Repo | Status | Nodes | Edges | Time`. Status values: `built`, `already built`, `skipped (<reason>)`, or the error message. Below that table, list the bundles and `_all` graph with their final node/edge counts. Do not append destructive-shell rebuild suggestions (e.g. `rm -rf graphs/<repo>`) - if the user wants a rebuild, that's their next call.

Notes for the build phase:
- The graphify CLI has no bare `graphify <path>` form - every call is a subcommand (`extract`, `update`, `cluster-only`, `merge-graphs`, ...). The pipeline above drives it from Python (`graphify.detect.detect`, `graphify.extract.extract`) so the `include_types` filter can be applied between detect and extract; only the `cluster-only` and `merge-graphs` steps shell out to the CLI.
- `graphify extract <path> --out <dir>` exists as a one-shot CLI and is fine for ad-hoc builds with no filter, but the `--include-types` flag does not exist - it is enforced by the Python-driven detect step above.
- `upstream/<repo>/` is read-only. Never write inside it.
- If a single repo build fails, continue with the rest. Collect failures and report at the end. The user can re-run `/bootstrap --build <repo>` to retry one.

Notes:
- Run each `git clone` as its own Bash tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`. Parallelize across repos in a single message.
- This command does NOT pull or switch. After bootstrap, run `/git-pull` to bring all repos to their latest tracked state (which also cascades graph updates for repos whose HEAD moved), `/git-switch <repo> <ref>` to pin one to a specific tag/branch, or `/graphify-update` to refresh graphs without touching git.
- This file is the canonical list of expected repos. `CLAUDE.md` and `README.md` reference it rather than duplicating the URLs.
- The graph build phase is independent of cloning. `/bootstrap --build <selector>` can be re-run after cloning to add graphs incrementally.
