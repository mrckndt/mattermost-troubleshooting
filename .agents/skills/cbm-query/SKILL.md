---
name: cbm-query
description: Run a raw Cypher query against a codebase-memory-indexed repo, for multi-hop or aggregation questions the other cbm-* skills can't answer.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] <cypher>`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and the remaining tokens form `<cypher>`.
- Otherwise, `<repo>` defaults to `mattermost` and the entire argument string is `<cypher>`.

1. Run `/cbm-index <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. If unsure what to query, first call `get_graph_schema` with `project` for node labels and edge types.
3. Call `query_graph` with `query` = `<cypher>`, `project`.
4. Present the returned rows as a table.
5. No rows: check whether the symbols queried fall under an excluded directory (see the excluded-dirs line from `/cbm-index <repo>`'s output) - `codebase-memory-mcp` excludes those from indexing entirely.
6. Note the 100k row ceiling; suggest adding `LIMIT` to `<cypher>` for broad queries.
