---
name: cbm-search
description: Find a symbol or definition in a codebase-memory-indexed repo by keyword or natural language (combines full-text and semantic search).
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] <query>`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and the remaining tokens form `<query>`.
- Otherwise, `<repo>` defaults to `mattermost` and the entire argument string is `<query>`.

1. Run `/cbm-index <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. Call `search_graph` with `project`, `query` = `<query>` verbatim, `semantic_query` = `<query>` split into individual keyword strings.
3. Present the top matches from `results`: `name`, `qualified_name`, `file_path:start_line`. If the response also has a `semantic_results` key, present those too; the key can be absent entirely (not just empty) even when `semantic_query` was passed - in that case say only BM25 `results` came back. Note `has_more`/`total` if truncated.
4. No matches: report it; note that `codebase-memory-mcp` hardcodes some directories out of indexing (e.g. `docs`, `build`, vendor dirs) - check the excluded-dirs line from `/cbm-index <repo>`'s output before assuming the symbol doesn't exist, and fall back to `rg`/`Read` for anything under an excluded path. Otherwise suggest `/cbm-query` for a raw Cypher search or broader keywords.
