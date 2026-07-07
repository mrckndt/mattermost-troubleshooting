---
name: cbm-get-code-snippet
description: Pull source code for a symbol from a codebase-memory-indexed repo, by qualified name or short name. Wraps get_code_snippet.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] <qualified name or short name>`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and the remaining tokens form the name.
- Otherwise, `<repo>` defaults to `mattermost` and the entire argument string is the name.

1. Run `/cbm-index-repository <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. This is a read tool, not a search tool - it needs an exact or close name.
   - If unsure of the exact qualified name, run `/cbm-search-graph <repo> <name>` first to find it.
   - Call `get_code_snippet` with `qualified_name` = the name (full qualified or short), `project`.
   - Pass `include_neighbors: true` to also pull immediately-connected symbols (e.g. a struct's methods) in the same call.
3. Present the file:line header, then the source.
4. Ambiguous (tool returns suggestions): list them and ask which one.
5. Not found: check whether the symbol's file falls under an excluded directory (see the excluded-dirs line from `/cbm-index-repository <repo>`'s output).
   - `codebase-memory-mcp` excludes those from indexing entirely; fall back to reading the file directly for anything under an excluded path.
