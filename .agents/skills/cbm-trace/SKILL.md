---
name: cbm-trace
description: Trace callers or callees of a function in a codebase-memory-indexed repo (e.g. "what calls ProcessOrder?").
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

1. Run `/cbm-index <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. Call `trace_path` with `function_name`, `project`, `direction`, `depth: 3`.
3. No results: run `/cbm-search <repo> <function name>` inline to find the closest candidates, present them, and ask which to trace. If that also finds nothing, check whether the function's file falls under an excluded directory (see the excluded-dirs line from `/cbm-index <repo>`'s output) before concluding it doesn't exist.
4. Present the chain grouped by `hop`, using `name`/`qualified_name` per node. `trace_path` does not return file locations - state this plainly and offer `/cbm-snippet <name>` for source on any specific hop.
