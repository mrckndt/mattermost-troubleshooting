---
name: cbm-search-code
description: Find a string literal, error message, or config value in a codebase-memory-indexed repo. Wraps search_code (graph-augmented grep); use cbm-search-graph for symbol search.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] <pattern>`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and the remaining tokens form `<pattern>`.
- Otherwise, `<repo>` defaults to `mattermost` and the entire argument string is `<pattern>`.

`search_graph`/`/cbm-search-graph` indexes symbol identifiers (function/class/route names). Use this skill for string literals, error messages, and config values.

This skill is the codebase-memory tool for that: it greps raw text, then deduplicates hits into their containing functions and ranks them (definitions first, popular functions next, tests last).

1. Run `/cbm-index-repository <repo>` inline, at most once per repo per session. If it already ran
   this session for `<repo>`, reuse the `Project` value it reported and skip re-running it.
   - If it reports MCP not present or the repo excluded, report the same and stop.
   - Otherwise, use the `Project` column from its output table as `project` below.
2. Call `search_code` with `project`, `pattern` = `<pattern>` verbatim.
   - Default `mode: compact` (signatures + metadata, token-efficient); `mode: full` also pulls source; `mode: files` returns just the file list.
   - Narrow with `file_pattern` (glob, e.g. `*.go`), `path_filter` (regex on result paths, e.g. `^server/`), or `context` (lines of context, compact mode only).
   - Pass `regex: true` to treat `<pattern>` as a regex instead of a literal.
3. Present the enriched results: function/symbol name, file:line, and (in `full` mode) source.
   - Report `total_grep_matches` (raw grep hit count) vs `total_results` (deduplicated function count) from the response.
4. **This tool caps at `limit` (default 10) with no `offset` parameter** - it surfaces ranked leads, not an exhaustive result set.
   - If `total_grep_matches` or `total_results` exceeds what was returned, say so plainly.
   - Raise `limit`, narrow with `file_pattern`/`path_filter`, or fall back to `rg --no-ignore --hidden -nF` for the exhaustive pass.
   - Report this tool's result as ranked leads plus the enclosing symbol for each match.
   - For the complete match set on an exact string (e.g. Phase 5 angle 1 of `/investigate`), cite
     `rg --no-ignore --hidden -n`.
5. No matches: report it.
   - `codebase-memory-mcp` hardcodes some directories out of indexing entirely, even under `mode: full` (e.g. `vendor`, `vendored`, `node_modules`, `.git`).
   - Check the excluded-dirs line from `/cbm-index-repository <repo>`'s output.
   - Non-code files (Dockerfiles, shell scripts, YAML) may also fall outside what got indexed.
   - Fall back to `rg --no-ignore --hidden -n` or reading the file directly for anything under an excluded path or a non-code file.
