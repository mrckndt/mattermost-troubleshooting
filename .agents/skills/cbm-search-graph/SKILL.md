---
name: cbm-search-graph
description: Find a symbol/definition (function, class, route, variable) by keyword or natural language. Wraps search_graph (symbol names, not source text); use cbm-search-code for text/literals.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] <query>`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and the remaining tokens form `<query>`.
- Otherwise, `<repo>` defaults to `mattermost` and the entire argument string is `<query>`.

1. Run `/cbm-index-repository <repo>` inline, at most once per repo per session. If it already ran
   this session for `<repo>`, reuse the `Project` value it reported and skip re-running it.
   - If it reports MCP not present or the repo excluded, report the same and stop.
   - Otherwise, use the `Project` column from its output table as `project` below.
2. Call `search_graph` with `project` and `query` = `<query>` verbatim (BM25 full-text over symbol identifiers, camelCase-split).
   - Run semantic search as its own call, passing `semantic_query` alone. A call carrying `query` returns BM25 results and omits `semantic_results`.
   - For semantic search (vector; bridges vocabulary, e.g. "publish" matches "send"), **omit `query`** and pass only
     `semantic_query` = the query split into keyword strings. That is a separate second call.
   - Both modes search **symbol names**. For string literals and error messages, use `/cbm-search-code`.
   - The `query` mode filters out `Variable`/`File`/`Folder`/`Module`-labeled nodes as noise - a named constant or config-struct field can legitimately return 0 hits even though it exists.
   - Config keys, setting names and feature-flag names are struct fields (e.g. `MaxOpenConns`), which this
     tool reports as 0 hits. Reach for `/cbm-search-code` or `rg` for those.
3. Present the top matches from `results`: `name`, `qualified_name`, `file_path:start_line`.
   - On a semantic-only call, read `semantic_results` (each with a `score`) and ignore `results`: with no `query` it
     degrades to an unfiltered match on the whole graph and is pure noise.
   - Note `has_more`/`total` if truncated (default `limit` is 50; pass `offset` to page).
4. For narrower or structural questions, use filters instead of / alongside `query`:
   - `label` (e.g. `Function`, `Route`), `name_pattern` (regex, exact matching).
   - `min_degree`/`max_degree` with `relationship` to filter by degree. For fan-in versus fan-out, use
     `/cbm-trace-path`, which resolves `inbound` and `outbound` separately.
   - `file_pattern` to scope by path.
5. No matches: report it.
   - `codebase-memory-mcp` hardcodes some directories out of indexing entirely, even under `mode: full` (e.g. `vendor`, `vendored`, `node_modules`, `.git`).
   - Before assuming the symbol doesn't exist, check the excluded-dirs line from `/cbm-index-repository <repo>`'s output.
   - Fall back to `rg --no-ignore --hidden -n` or reading the file directly for anything under an excluded path.
   - Otherwise suggest `/cbm-search-code` if the target may be a text literal or a struct field, or broader keywords.
