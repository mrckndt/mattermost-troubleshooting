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

2. **Resolve build set**: read `graphs/config.json`. For a `<bundle-name>` selector, take `bundles.<bundle-name>.repos`. For `all`, take all keys under `repos`. For a single `<repo>`, take just that one. Validate that each repo exists under `upstream/<repo>/`; if not, skip it with a warning row in the report.

3. **For each repo in the build set** (run in parallel via separate Bash tool calls where independent; do not chain with `&&` or pipes):
   - If `graphs/<repo>/graphify-out/graph.json` already exists, skip with status `already built` (idempotent).
   - Resolve `include_types` for this repo: per-repo `repos.<repo>.include_types` if present, else `defaults.include_types`, else all categories. Phase 1 default is `["code", "document"]`.
   - For `scope: full`: follow the graphify skill pipeline at `~/.claude/skills/graphify/SKILL.md` with one modification - apply the `include_types` filter to the detect output before extraction:
     - Call `graphify.detect.detect(upstream/<repo>)` from Python.
     - Zero out every `result['files'][k]` where `k` is not in the resolved `include_types`. Recompute `total_files` and `total_words`.
     - Write `.graphify_detect.json` under `graphs/<repo>/graphify-out/`.
     - Continue with the SKILL.md pipeline (AST extraction, semantic subagents if any non-code categories survived, build, cluster, report). Working directory: `graphs/<repo>/`.
   - For `scope: subdirs`: per-subdir graphs live persistently under `graphs/<repo>/<subdir-name>/graphify-out/`. The subdir-name is the relative path with slashes replaced by underscores (e.g. `server/channels/app` → `server_channels_app`). For each path in `repos.<repo>.paths`, run the SKILL.md flow (same filter as above) against `upstream/<repo>/<path>` with the working directory set to `graphs/<repo>/<subdir-name>/`, so the per-subdir `graphify-out/` lands there. Write `.graphify_root` in each per-subdir `graphify-out/` pointing to `upstream/<repo>/<path>` (used by `/graphify-update`). After all subdirs are built, merge them into the top-level graph: `graphify merge-graphs graphs/<repo>/*/graphify-out/graph.json --out graphs/<repo>/graphify-out/graph.json`, then re-cluster: `graphify cluster-only graphs/<repo>/ --no-viz`. Do not delete the per-subdir directories - they are required for incremental updates.
   - Write `graphs/<repo>/.meta.json` with:
     ```
     { "ref": "<git -C upstream/<repo> rev-parse HEAD>", "built_at": "<ISO timestamp>", "scope": "full|subdirs" }
     ```

4. **Cascade re-merge**: after per-repo builds, for each bundle in `graphs/config.json#/bundles` whose `repos` list is fully built (every member has `graphs/<member>/graphify-out/graph.json`), merge into `graphs/_bundles/<bundle>/graphify-out/graph.json` with `graphify merge-graphs`, then `graphify cluster-only graphs/_bundles/<bundle>/ --no-viz`. Skip bundles with missing members and report them.

5. **`_all` graph**: merge every existing per-repo `graph.json` into `graphs/_all/graphify-out/graph.json`, then `graphify cluster-only graphs/_all/ --no-viz`. (The user can pin `_all` via `/graphify-scope _all` for cross-cutting questions.)

6. **Report**: extend the clone summary with a second Markdown table titled `Graph build`. Columns: `Repo | Status | Nodes | Edges | Time`. Status values: `built`, `already built`, `skipped (<reason>)`, or the error message. Below that table, list the bundles and `_all` graph with their final node/edge counts.

Notes for the build phase:
- Driving graphify always uses the Python entry from `~/.claude/skills/graphify/SKILL.md` so the `include_types` filter can be applied. The bare `graphify <path>` CLI is only correct when no filter is needed. Either way, the working directory is `graphs/<repo>/` (or `graphs/<repo>/<subdir-name>/` for subdir builds) so output lands next to it in `graphify-out/`.
- `upstream/<repo>/` is read-only. Never write inside it.
- If a single repo build fails, continue with the rest. Collect failures and report at the end. The user can re-run `/bootstrap --build <repo>` to retry one.

Notes:
- Run each `git clone` as its own Bash tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`. Parallelize across repos in a single message.
- This command does NOT pull or switch. After bootstrap, run `/git-pull` to bring all repos to their latest tracked state (which also cascades graph updates for repos whose HEAD moved), `/git-switch <repo> <ref>` to pin one to a specific tag/branch, or `/graphify-update` to refresh graphs without touching git.
- This file is the canonical list of expected repos. `CLAUDE.md` and `README.md` reference it rather than duplicating the URLs.
- The graph build phase is independent of cloning. `/bootstrap --build <selector>` can be re-run after cloning to add graphs incrementally.
