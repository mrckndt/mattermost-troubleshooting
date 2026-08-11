---
name: cbm-index-repository
description: Index one or more upstream/<repo> clones (or every non-excluded repo) into the codebase-memory knowledge graph, skipping any repo already indexed at its current HEAD sha. Wraps index_repository.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: zero, one, or several `<repo>` names matching directories under `upstream/`.

If `mcp__codebase_memory_local__*` is absent: report `codebase-memory MCP not present` and stop.

**Project name derivation** (used throughout): absolute repo path with the leading `/` stripped and each
remaining `/` replaced by `-` (e.g. `/Users/foo/upstream/mattermost` -> `Users-foo-upstream-mattermost`).

Read `"$PROJECT_ROOT/.agents/config/repos.json"`'s `repos` array; `excluded` = the set of `name` values
with `cbm_excluded: true` (currently `enterprise`; see that entry's `cbm_excluded_reason`).
**Fail closed:** if this file is missing or fails to parse, stop and report the error - never proceed
with an assumed-empty `excluded` set.

Build the target list:
- Args given: exactly those names. Verify each `upstream/<repo>/` exists; if one does not, list what is
  under `upstream/` and drop that name, continuing with the rest.
- No args: every `name` in `repos.json`'s `repos` array. Note any without a clone on disk as
  `<repo>: not cloned, skipped (run /bootstrap)` and drop it.

**Excluded repos are never indexed - no argument, flag, or phrasing overrides this, and no code path
below this point may call any codebase-memory MCP tool (including `index_status`) for a name in
`excluded`.** For each name in the target list that is also in `excluded`: report
`<repo> excluded from codebase-memory (<cbm_excluded_reason>); use rg/grep against upstream/<repo>/
directly` and drop it from the target list. Zero MCP calls for that name - do this filtering purely from
`repos.json` and the target list, before any codebase-memory MCP call of any kind.

Read `"$PROJECT_ROOT/upstream/.cbm-index-cache.json"` once as `cache` (missing or unparseable counts as `{}`).

For each remaining target repo:
1. `ref` = `git -C "$PROJECT_ROOT/upstream/<repo>" describe --tags --exact-match 2>/dev/null || git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD`.
   Same resolution `/git-switch`/`/version-lookup` treat as the repo's identity.
2. `sha` = `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse HEAD`. `clean` = `git -C "$PROJECT_ROOT/upstream/<repo>" status --porcelain` prints nothing.
3. `project` = derived project name (see above).
4. Skip the real index (`state = unchanged`) only if all of:
   - `cache[<repo>]` exists,
   - `cache[<repo>].head_sha == sha`,
   - `clean` is true,
   - `index_status(project)` reports `status: "ready"` and `nodes == cache[<repo>].nodes`.
   Take `nodes`/`edges`/`excluded` for the report from `cache[<repo>]`; do not call `index_repository`.
5. Otherwise (`state = reindexed`): call `index_repository` with `repo_path` = absolute `upstream/<repo>`,
   `mode: full`, `persistence: false`.
   - On error: note it, leave `cache[<repo>]` untouched, continue to the next repo.
   - On success: set `cache[<repo>] = {"ref": ref, "head_sha": sha, "indexed_at": <UTC now, via
     `date -u +%Y-%m-%dT%H:%M:%SZ`>, "nodes": <nodes>, "edges": <edges>, "excluded": <excluded>}` from the
     response.

After the loop, write `cache` back to `"$PROJECT_ROOT/upstream/.cbm-index-cache.json"` once, merged with its
on-disk contents so repos outside this run's target list keep their existing entries untouched.

Report a Markdown table: `Repo | Project | State | Ref | Nodes | Edges` (`State` = `reindexed` or `unchanged`
from step 4/5; the rest from `ref` above plus the response, or `cache[<repo>]` on a skip).
- One line per processed repo (reindexed or unchanged), from `excluded` (the response on a reindex,
  `cache[<repo>].excluded` on a skip): `Excluded (<repo>): <count> dirs (<comma-joined dirs list>)`.
  `codebase-memory-mcp` excludes these directories from indexing entirely (no results, not "not found"); the
  other `cbm-*` skills point back here when a search unexpectedly comes up empty.
- One line per policy-excluded repo and per not-cloned repo, as worded above.

Notes:
- `mode: full`, always: `moderate`/`fast` hardcode out dirs like `public`, `i18n`, `migrations`, blinding
  `cbm-*` to `server/public` (the `model`/`client4` module) in `mattermost`. Switching modes on an
  already-indexed repo also fails codebase-memory-mcp's incremental-eligibility check internally, forcing a
  full reindex either way - so there's no cheaper mode to reach for later.
- `persistence: false`, always: `true` writes `.codebase-memory/graph.db.zst` into the working tree and sets
  `merge.ours.driver` in that clone's git config, blocking a later `/git-switch`. Once such an artifact
  exists it's rewritten on every run regardless of the flag; delete `upstream/<repo>/.codebase-memory/` if
  one appears.
- Reindexing is never free, even unchanged - one changed file reloads and rebuilds the whole graph
  (similarity, semantic edges, the search index) from scratch, and cost scales with repo size. That per-run
  cost is exactly what repeated, ungated `/investigate` runs were paying.
- codebase-memory-mcp's own file cache keys on mtime+size, not content hash. `git switch`/`git checkout`
  rewrites file mtimes even returning to a byte-identical commit, so that internal cache never recognizes a
  post-switch repo as unchanged - a reindex right after a switch-away-and-back costs the same as a real
  content change. This skill's `head_sha` gate exists because of that: skip the whole `index_repository`
  call outright, don't rely on the tool's internal cache to no-op.
- The gate is exact, not heuristic: `head_sha` matching means the working tree is provably the same commit
  (detached tag or branch alike); `clean` rules out uncommitted edits at that commit. No false-skip window.
- Reindexing the same commit twice back-to-back reproduces the same node/edge counts, but reindexing after
  a switch away and back can drift slightly from the pre-switch counts on the same commit. The
  `nodes == cache[<repo>].nodes` condition guards against a corrupted/partial persisted index, not exact
  reproducibility across separate `index_repository` calls.
- Indexing is serialized inside codebase-memory-mcp - a no-arg run over every repo runs strictly one at a
  time, not in parallel.
- `cbm_excluded` in `repos.json` is a policy decision (private/license-gated repos), distinct from the
  excluded-dirs list above, which is a tool limitation - use `rg`/`git` against `upstream/<repo>/` for those.
- `upstream/.cbm-index-cache.json` is the skip gate's source of truth: gitignored, sits outside every
  clone's working tree (untouched by `/git-switch` or `git status`), and is read-merge-written so repos
  outside the current run's target list keep their existing entries.
- This is the manual equivalent of Phase 5 Step 0 in `/investigate`; use it for ad-hoc codebase-memory
  queries outside `/investigate`, e.g. after a manual `/git-switch` (correctly forces a real reindex here,
  since the sha changes). Every other `cbm-*` skill calls this skill first as its presence check.
- If a project's index looks corrupt or stale in a way a real reindex doesn't fix: call `delete_project`
  with the project name, drop its `cache[<repo>]` entry, then reindex from scratch. Surgical alternative to
  wiping all of `~/.cache/codebase-memory-mcp/`.
