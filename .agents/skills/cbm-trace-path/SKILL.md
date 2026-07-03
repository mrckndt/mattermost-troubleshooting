---
name: cbm-trace-path
description: Trace callers or callees of a function in a codebase-memory-indexed repo (e.g. "what calls ProcessOrder?"). Wraps trace_path.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] <question or function name>`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and the remaining tokens form the question/function name.
- Otherwise, `<repo>` defaults to `mattermost` and the entire argument string is the question/function name.

Determine `direction` from phrasing, then extract the function name from whatever remains:
- "what calls X" / "callers of X" -> `inbound`.
- "what does X call" / "callees of X" -> `outbound`.
- Unspecified / "trace X" -> `both`.

1. Run `/cbm-index-repository <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. Call `trace_path` with `function_name`, `project`, `direction`, `depth: 3`.
   - Default `mode` is `calls` (follows `CALLS` edges).
   - `mode: data_flow` adds arg expressions at each hop, optionally scoped with `parameter_name`.
   - `mode: cross_service` follows `HTTP_CALLS`/`ASYNC_CALLS`/`DATA_FLOWS` through Route nodes.
   - `risk_labels: true` classifies each hop CRITICAL/HIGH/MEDIUM/LOW by distance.
   - `include_tests: true` keeps test-file callers (excluded by default); `edge_types` restricts to specific edges.
3. No results: run `/cbm-search-graph <repo> <function name>` inline for the closest candidates, present them, and ask which to trace.
   - If that also finds nothing, check whether the function's file falls under an excluded directory before concluding it doesn't exist.
   - See the excluded-dirs line from `/cbm-index-repository <repo>`'s output.
4. Present the chain grouped by `hop`, using `name`/`qualified_name` per node.
   - `trace_path` does not return file locations; state this plainly and offer `/cbm-get-code-snippet <name>` for source on any hop.
