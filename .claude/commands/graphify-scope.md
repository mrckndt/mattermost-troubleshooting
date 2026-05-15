---
description: Show, pin, or clear the active graphify scope. Determines which knowledge graph queries hit.
argument-hint: [<scope> | clear]
---

First verify the shell is at the project root - a prior skill/tool may have left it in a subdirectory, silently misrouting relative paths like `graphs/<scope>`. Run `pwd && ls -1 CLAUDE.md README.md .gitignore .claude claude-md upstream graphs`. If `pwd` doesn't end in `/mattermost-troubleshooting` or any entry is missing, `cd` (absolute path) to the root before continuing. (If `graphs/` itself is missing, advise the user to run `/bootstrap` first - the rest of this command needs `graphs/config.json`.)

Args: $ARGUMENTS

Behavior depends on the argument.

## No argument: show available scopes

1. Read `graphs/.active_scope` if it exists; the contents (trimmed) is the pinned scope path relative to `graphs/`. If the file is absent or empty, no scope is pinned.
2. Enumerate available scopes:
   - **repo** scopes: every directory `graphs/<name>/` where `graphs/<name>/graphify-out/graph.json` exists.
   - **bundle** scopes: every directory `graphs/_bundles/<name>/` where `graphs/_bundles/<name>/graphify-out/graph.json` exists.
3. Report a Markdown table with columns `Scope | Type | Pinned`. `Type` is `repo` or `bundle`. `Pinned` is `*` for the pinned row, empty otherwise. Sort: repos alphabetically, then bundles alphabetically.
4. If no scopes are built yet, print: `No scopes built. Run /bootstrap --build-graphs <bundle-name|all|repo-name> first (see graphs/config.json for defined bundles and repos).`

## `clear` argument: remove the pin

1. If `graphs/.active_scope` exists, delete it (`rm graphs/.active_scope`).
2. Report `Scope unpinned. Auto-select resumes.`

## `<scope>` argument: pin a scope

1. Resolve `<scope>` to a directory, in this order:
   - `graphs/<scope>/` if it exists (per-repo scope).
   - `graphs/_bundles/<scope>/` if it exists (bundle scope).
2. If the resolved directory does not contain `graphify-out/graph.json`, list the available scopes (same enumeration as the no-argument case) and stop with `Scope '<scope>' is not built. Available scopes listed above.`
3. Otherwise, write the resolved relative path on a single line to `graphs/.active_scope`. The path is:
   - `<repo>` for a per-repo scope.
   - `_bundles/<bundle-name>` for a bundle scope.
4. Report `Scope pinned to graphs/<resolved>/. All subsequent graphify queries use this scope until /graphify-scope clear.`

## Notes

- The auto-select heuristic in `CLAUDE.md` only runs when `graphs/.active_scope` is absent or empty.
- Per-repo and bundle names are sourced from disk (which scopes are built), not from `graphs/config.json`. A scope listed in `config.json` but not yet built will not appear here.
- Per-repo and bundle definitions live in `graphs/config.json`. To enable a new repo or change scope shape, edit that file and rebuild.
- Run each Bash invocation as a separate tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`.
