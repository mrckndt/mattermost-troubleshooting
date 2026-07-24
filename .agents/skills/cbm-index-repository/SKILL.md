---
name: cbm-index-repository
description: Reindex an upstream/<repo> clone (or all indexed repos) into the codebase-memory knowledge graph. Wraps index_repository, skipped when a per-repo ref cache shows nothing changed.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: optionally a single `<repo>` name matching a directory under `upstream/`.

If `mcp__codebase_memory_local__*` is absent: report `codebase-memory MCP not present` and stop.

Read `"$PROJECT_ROOT/upstream/.cbm-index-cache.json"` as `cache` (missing or unparseable counts as `{}`).

**Project name derivation** (used throughout): absolute repo path with the leading `/` stripped and each
remaining `/` replaced by `-` (e.g. `/Users/foo/upstream/mattermost` -> `Users-foo-upstream-mattermost`).

**`enterprise` is permanently excluded** (private, license-gated repo; data sensitivity). If `<repo>` is
`enterprise`: derive its project name; if `index_status` reports it indexed, call `delete_project` to purge it.
Drop `cache["enterprise"]` if present and write `cache`. Report
`enterprise excluded from codebase-memory (private/license-gated); use rg/grep against upstream/enterprise/ directly` and stop.

Determine repos to process:
- Arg given: verify `upstream/<repo>/` exists (if not, list available repos under `upstream/` and stop). Process that repo only.
- No arg: call `list_projects` once as `snapshot`; process every entry whose `root_path` does not end in `/enterprise`.
  For any `enterprise` entry: call `delete_project` with its `name`, drop its cache entry, and note
  `enterprise: excluded (private/license-gated), index purged` in the final report.

For each repo to process:

1. `ref` = `git -C "$PROJECT_ROOT/upstream/<repo>" describe --tags --exact-match 2>/dev/null || git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD`.
   Same resolution `/git-switch`/`/version-lookup` treat as the repo's identity.
   `clean` = `git -C "$PROJECT_ROOT/upstream/<repo>" status --porcelain` prints nothing.
2. `project` = derived project name (see above). `proj` = the matching `snapshot` entry, if one was fetched (no-arg mode).
3. Skip the real index only if `cache[<repo>].ref == ref`, `clean` is true, and `nodes > 0` where `nodes`/`status`
   come from `proj` if it exists, else from `index_status(project)`. Otherwise:
   - Call `index_repository` with `repo_path` = absolute `upstream/<repo>`, `mode: full`, `persistence: false`.
   - On error: continue to the next repo; leave `cache[<repo>]` untouched (retried for real next run).
   - On success: call `index_status(project)` for `nodes`/`edges` (fall back to `list_projects` matched by
     `root_path` if `index_status` errors); set `cache[<repo>] = {"ref": ref, "indexed_at": <UTC now>}`.

After the loop, write `cache` back to `"$PROJECT_ROOT/upstream/.cbm-index-cache.json"` once.

Report a Markdown table: `Repo | Project | Ref | Nodes | Edges` (`Ref` = `ref`, rest from `proj`/`index_status`).
- One line per skipped repo: `Unchanged (<repo>): ref matches last run (<ref>), reindex skipped.`
- One line per repo actually reindexed this run, from `index_repository`'s `excluded` field: `Excluded (<repo>): <count> dirs (<comma-joined dirs list>)`.
- `codebase-memory-mcp` excludes these directories from indexing entirely (no results, not "not found"); the other `cbm-*` skills point back here when a search unexpectedly comes up empty.

Notes:
- `enterprise` exclusion is a policy decision (data sensitivity), not a tool limitation like the excluded-dirs
  list below - it never gets indexed, purged if a stale index exists. Use `rg`/`git` against `upstream/enterprise/` directly.
- `index_status(project)` replaces `list_projects` on the single-repo cache-hit path to avoid fetching every
  other indexed project's metadata just to check one repo's node count.
- `mode: full` (not `moderate`): `moderate` hardcodes out dirs named `public`, `i18n`, `migrations`, and similar
  regardless of content. That blinded every `cbm-*` skill to `server/public` (the `model`/`client4` module) in
  `mattermost`/`enterprise`.
- This is the manual equivalent of Phase 5 Step 0 in `/investigate`; use it for ad-hoc codebase-memory queries outside `/investigate`, e.g. after a manual `/git-switch`.
- `index_repository` always walks the full tree before it can even tell nothing changed, and has no notion of git ref at all.
- Its own file-level cache is mtime+size, not a real content hash - the `sha256` field it stores is an empty string.
- `upstream/.cbm-index-cache.json` is our own layer on top: gitignored, and sits outside every repo clone's working tree (untouched by `/git-switch`, invisible to that clone's `git status`).
- The cache key is the ref label, not a commit sha: a detached tag (`v10.11.19`) is immutable, so this is exact.
- On a moving branch (`master`, `release-11.7`) the label can't detect new commits landing on that branch without a `/git-switch` in between.
- Accepted: customer investigations mostly pin to a specific tag, and cross-version differences dwarf a few trailing branch commits.
- The false-skip window is small and cheap to fix (`/git-switch` or `delete_project`).
- A repo with no cache entry (first run, or indexed manually outside this skill) always gets a real index.
- Every other `cbm-*` skill calls this skill first as its presence check; repeated calls for an unchanged repo are cheap now because of this cache, not `index_repository`'s own incrementalism.
- `persistence: false` always - `true` would write into the working tree and block a later `/git-switch`.
- If a project's index looks corrupt or stale in a way reindexing doesn't fix: call `delete_project` with `project`, then reindex from scratch (self-heals the cache too).
- That's a surgical alternative to wiping all of `~/.cache/codebase-memory-mcp/`.
