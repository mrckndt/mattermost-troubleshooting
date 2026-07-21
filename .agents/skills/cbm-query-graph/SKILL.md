---
name: cbm-query-graph
description: Run a raw Cypher query against a codebase-memory-indexed repo, for multi-hop or aggregation questions the other cbm-* skills can't answer. Wraps query_graph.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] <cypher>`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and the remaining tokens form `<cypher>`.
- Otherwise, `<repo>` defaults to `mattermost` and the entire argument string is `<cypher>`.

1. Run `/cbm-index-repository <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. If unsure what to query, first call `get_graph_schema` with `project` for node labels and edge types.
3. Call `query_graph` with `query` = `<cypher>`, `project`. Optionally pass `max_rows` to cap the result.
4. Present the returned rows as a table (`total` in the response is the returned row count).
5. No rows: check whether the symbols queried fall under an excluded directory (see the excluded-dirs line from `/cbm-index-repository <repo>`'s output).
   - `codebase-memory-mcp` excludes those from indexing entirely.
6. Note the 100k row ceiling. There is no `offset` support here - use `/cbm-search-graph` with `offset`/`limit` for paginated browsing instead.
   - Add `LIMIT` in `<cypher>` for broad queries.
   - `Function` (no receiver) vs `Method` (has a receiver) reflects real Go semantics, not an indexing inconsistency - a `(f:Method)` filter can silently miss a related free function in the same file.
   - When searching for "any function/method that does X", omit the label or match both rather than assuming one.
7. For performance/hot-path questions, every `Function`/`Method` node carries queryable complexity properties:
   - `cyclomatic`, `cognitive`, `loop_count`, `loop_depth` (max nested-loop depth).
   - `transitive_loop_depth`: worst-case nested-loop degree propagated along `CALLS` edges (interprocedural).
   - `recursive`, `linear_scan_in_loop` (find/contains/indexOf-style scans in a loop - the hidden O(n^2) that `loop_depth` misses).
   - `alloc_in_loop`, `recursion_in_loop`, `unguarded_recursion`, `param_count`, `max_access_depth`.
   - Example:
     ```
     MATCH (f:Function) WHERE f.transitive_loop_depth >= 3 OR f.linear_scan_in_loop >= 1
     RETURN f.qualified_name, f.transitive_loop_depth, f.linear_scan_in_loop
     ORDER BY f.transitive_loop_depth DESC
     ```
