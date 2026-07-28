---
name: cbm-index-repository
description: Index one or more upstream/<repo> clones (or every non-excluded repo) into the codebase-memory knowledge graph. Wraps index_repository.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: zero, one, or several `<repo>` names matching directories under `upstream/`.

If `mcp__codebase_memory_local__*` is absent: report `codebase-memory MCP not present` and stop.

**Project name derivation** (used throughout): absolute repo path with the leading `/` stripped and each
remaining `/` replaced by `-` (e.g. `/Users/foo/upstream/mattermost` -> `Users-foo-upstream-mattermost`).

Read `"$PROJECT_ROOT/.agents/config/repos.json"`'s `repos` array; `excluded` = the set of `name` values
with `cbm_excluded: true` (currently `enterprise`; see that entry's `cbm_excluded_reason`).

Build the target list:
- Args given: exactly those names. Verify each `upstream/<repo>/` exists; if one does not, list what is
  under `upstream/` and drop that name, continuing with the rest.
- No args: every `name` in `repos.json`'s `repos` array. Note any without a clone on disk as
  `<repo>: not cloned, skipped (run /bootstrap)` and drop it.

**Excluded repos are never indexed - no argument, flag, or phrasing overrides this.** For each name in the
target list that is also in `excluded`: derive its project name, call `delete_project`
(`status: "not_found"` means nothing to purge, not an error), report
`<repo> excluded from codebase-memory (<cbm_excluded_reason>); use rg/grep against upstream/<repo>/ directly`,
and drop it from the target list. Do this before any `index_repository` call.

For each remaining target repo:
1. Call `index_repository` with `repo_path` = absolute `upstream/<repo>`, `mode: full`, `persistence: false`.
   On error: note it, continue to the next repo.
2. `ref` = `git -C "$PROJECT_ROOT/upstream/<repo>" describe --tags --exact-match 2>/dev/null || git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD`.
   Same resolution `/git-switch`/`/version-lookup` treat as the repo's identity.

After the loop, write `"$PROJECT_ROOT/upstream/.cbm-index-cache.json"` once: per indexed repo,
`{"ref": ref, "indexed_at": <UTC now>, "nodes": <nodes>, "edges": <edges>}` from that repo's
`index_repository` response.

Report a Markdown table: `Repo | Project | Ref | Nodes | Edges`, all from the response plus `ref` above.
- One line per repo, from that response's `excluded` field: `Excluded (<repo>): <count> dirs (<comma-joined dirs list>)`.
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
- Reindex cost tracks content, not repo size: an unchanged repo is a near-instant no-op internally. One
  changed file reloads and rebuilds the whole graph (similarity, semantic edges, the search index) from
  scratch. codebase-memory-mcp's own file cache keys on mtime+size, not content hash, so any `/git-switch`
  pays that full cost even switching back to a ref indexed before.
- Indexing is serialized inside codebase-memory-mcp - a no-arg run over every repo runs strictly one at a
  time, not in parallel.
- `cbm_excluded` in `repos.json` is a policy decision (private/license-gated repos), distinct from the
  excluded-dirs list above, which is a tool limitation - use `rg`/`git` against `upstream/<repo>/` for those.
- `upstream/.cbm-index-cache.json` is a record of what was indexed and when, not a skip gate: it's
  gitignored, sits outside every clone's working tree, and is untouched by `/git-switch` or `git status`.
- This is the manual equivalent of Phase 5 Step 0 in `/investigate`; use it for ad-hoc codebase-memory
  queries outside `/investigate`, e.g. after a manual `/git-switch`. Every other `cbm-*` skill calls this
  skill first as its presence check.
- If a project's index looks corrupt or stale in a way reindexing doesn't fix: call `delete_project` with
  the project name, then reindex from scratch. Surgical alternative to wiping all of
  `~/.cache/codebase-memory-mcp/`.
