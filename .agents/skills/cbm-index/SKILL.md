---
name: cbm-index
description: Reindex an upstream/<repo> clone (or all indexed repos) into the codebase-memory knowledge graph. No-op-fast when unchanged, incremental after a version switch.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: optionally a single `<repo>` name matching a directory under `upstream/`.

If `mcp__codebase_memory_local__*` is absent: report `codebase-memory MCP not present` and stop.

- If an argument is given: verify `upstream/<repo>/` exists (if not, list available repos and stop). Reindex that repo only.
- If no argument: call `list_projects`; reindex every project it reports.

For each repo to reindex:

1. Call `index_repository` with `repo_path` = absolute `upstream/<repo>`, `mode: moderate`, `persistence: false`.
2. Call `list_projects`; find the entry whose `root_path` matches this repo.
3. `git -C "$PROJECT_ROOT/upstream/<repo>" describe --tags --exact-match 2>/dev/null || git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD` to report the current ref.
4. Continue on error.

Report a Markdown table: `Repo | Project | Ref | Nodes | Edges`. Under the table, for each repo add a line from `index_repository`'s `excluded` field: `Excluded (<repo>): <count> dirs (<comma-joined dirs list>)`. `codebase-memory-mcp` excludes these directories from indexing entirely (no results, not "not found") - the other `cbm-*` skills point back here when a search unexpectedly comes up empty.

Notes:
- This is the manual equivalent of Phase 5 Step 0 in `/investigate`; use it for ad-hoc codebase-memory queries outside `/investigate`, e.g. after a manual `/git-switch`.
- `persistence: false` always - `true` would write into the working tree and block a later `/git-switch`.
