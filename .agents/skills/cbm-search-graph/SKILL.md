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

1. Run `/cbm-index-repository <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop.
   - Use the `Project` column from its output table as `project` below.
2. Call `search_graph` with `project` and `query` = `<query>` verbatim (BM25 full-text over symbol identifiers, camelCase-split).
   - Also pass `semantic_query` = `<query>` split into individual keyword strings (vector search; bridges vocabulary, e.g. "publish" matches "send").
   - Both modes search **symbol names**, not source text. This tool cannot find string literals or error messages; use `/cbm-search-code` for that.
   - The `query` mode filters out `Variable`/`File`/`Folder`/`Module`-labeled nodes as noise - a named constant or config-struct field can legitimately return 0 hits even though it exists.
   - Use `/cbm-query-graph` (raw Cypher has no such filter) or grep to reach those.
3. Present the top matches from `results`: `name`, `qualified_name`, `file_path:start_line`.
   - If the response also has a `semantic_results` key, present those too. The key can be absent entirely (not just empty) even when `semantic_query` was passed - say only BM25 `results` came back.
   - Note `has_more`/`total` if truncated (default `limit` is 200; pass `offset` to page).
4. For narrower or structural questions, use filters instead of / alongside `query`:
   - `label` (e.g. `Function`, `Route`), `name_pattern` (regex, exact matching).
   - `min_degree`/`max_degree` with `relationship` and `direction` for fan-in/fan-out; `max_degree: 0` + `exclude_entry_points: true` surfaces dead code.
   - `file_pattern` to scope by path.
5. No matches: report it.
   - `codebase-memory-mcp` hardcodes some directories out of indexing entirely (e.g. `docs`, `build`, vendor dirs).
   - Before assuming the symbol doesn't exist, check the excluded-dirs line from `/cbm-index-repository <repo>`'s output.
   - Fall back to `rg`/`Read` for anything under an excluded path.
   - Otherwise suggest `/cbm-query-graph` for a Cypher search, `/cbm-search-code` if the target may be a text literal, or broader keywords.
