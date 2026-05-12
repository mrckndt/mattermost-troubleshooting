---
description: List, add, or remove knowledge-graph bundles. Bundles group repos for cross-repo graph queries.
argument-hint: [<name> | add <name> [<repos>] [<keywords>] | remove <name>]
---

First verify the shell is at the project root - a prior skill/tool may have left it in a subdirectory, silently misrouting relative paths like `graphs/config.json`. Run `pwd && ls -1 CLAUDE.md README.md .gitignore .claude claude-md upstream graphs`. If `pwd` doesn't end in `/mattermost-troubleshooting` or any entry is missing, `cd` (absolute path) to the root before continuing. (If `graphs/` itself is missing, advise the user to run `/bootstrap` first - the rest of this command needs `graphs/config.json`.)

Args: $ARGUMENTS

Behavior depends on the argument. All mutations edit `graphs/config.json` in place. Both `repos` and `keywords` are optional in a bundle definition: a bundle with no `repos` is skipped during merge (`/graphify-update`, `/bootstrap` cascade); a bundle with no `keywords` simply won't trigger keyword-based auto-selection (it can still be pinned via `/graphify-scope`).

**Repo name resolution**: a valid repo name is a folder under `upstream/` (which matches the path component after `https://github.com/mattermost/` in `/bootstrap`'s URL list). Names with a stripped `mattermost-` prefix are accepted as shorthand and resolved (e.g. `plugin-github` -> `mattermost-plugin-github`). Unresolved names are reported with a warning but accepted into the config (the user may be adding a repo not yet cloned).

## No argument: list bundles

1. Read `graphs/config.json#/bundles`. If absent or empty, print `No bundles defined. Use /graphify-bundle add <name> to create one.` and stop.
2. For each bundle, check whether `graphs/_bundles/<name>/graphify-out/graph.json` exists.
3. Report a Markdown table with columns `Bundle | Repos | Keywords | Built`.
   - `Repos`, `Keywords`: comma-separated values, or `—` if missing/empty.
   - `Built`: `yes` or `no`.

## `<name>` argument: show bundle details

1. Look up `<name>` under `graphs/config.json#/bundles`. If not found, list the defined bundles (same enumeration as the no-argument case) and stop with `Bundle '<name>' not found. Defined bundles listed above.`
2. Print the bundle's `repos` and `keywords` as bullet lists (`(none)` when empty).
3. State whether the bundle graph is built. If built, include the node count from `graphs/_bundles/<name>/graphify-out/graph.json`.

## `add <name> [<repos>] [<keywords>]` argument: create a bundle

Tokens after `add`:
- `<name>` (required): bundle name. Must not already exist.
- `<repos>` (optional): comma-separated repo names. Omit for an empty bundle.
- `<keywords>` (optional): comma-separated keywords. Omit for no auto-select.

Steps:
1. If `<name>` already exists in `graphs/config.json#/bundles`, stop with: `Bundle '<name>' already exists. Remove it first with /graphify-bundle remove <name>, or edit graphs/config.json directly.`
2. Resolve each repo name (see Repo name resolution). Warn inline for any unresolved.
3. Build the bundle object: `{"repos": [...], "keywords": [...]}`. Omit the `repos` key if the resolved list is empty; omit `keywords` if no keywords were given.
4. Show the user what would be written (the JSON snippet for the new bundle entry) and ask: `This will add bundle '<name>' to graphs/config.json. Continue? [y/N]`. Stop if the answer (case-insensitive, trimmed) is not `y` or `yes`.
5. Insert under `graphs/config.json#/bundles/<name>` and write the file back (`json.dumps` with `indent=2`, preserve `_`-prefixed metadata keys, trailing newline).
6. Report: `Bundle '<name>' added.` then a one-line hint: `Run /graphify-update <name> to build the bundle graph.` (omit the hint if repos is empty).

## `remove <name>` argument: delete a bundle

1. If `<name>` is not in `graphs/config.json#/bundles`, list the defined bundles (same enumeration as the no-argument case) and stop with `Bundle '<name>' not found. Defined bundles listed above.`
2. Show the user what will be removed (the current JSON snippet for the bundle) and whether `graphs/_bundles/<name>/` exists on disk. Ask: `This will remove bundle '<name>' from graphs/config.json and delete graphs/_bundles/<name>/ if present. Continue? [y/N]`. Stop if the answer (case-insensitive, trimmed) is not `y` or `yes`.
3. Remove the entry from `graphs/config.json#/bundles/<name>` and write the file back.
4. If `graphs/_bundles/<name>/` exists, delete the directory (including `graphify-out/`, `.meta.json`, any other contents). Report: `Removed config entry and deleted graphs/_bundles/<name>/.`
5. If the directory doesn't exist, report: `Removed config entry (no graph was built).`
6. If `graphs/.active_scope` contained `_bundles/<name>`, delete `graphs/.active_scope` and append: `Active scope pin cleared.`

## Notes

- Bundle definitions are sourced from `graphs/config.json#/bundles` (the listing reflects what's defined, not what's built). The `Built` column reflects what's on disk.
- `repos` and `keywords` are optional. Behaviour with missing values: empty `repos` -> bundle skipped during merge; empty `keywords` -> bundle excluded from keyword auto-select but still pinnable.
- To modify an existing bundle's repos or keywords, edit `graphs/config.json` directly, or `remove` and re-`add` the bundle. The slash command is intentionally narrow (list/add/remove); finer-grained edits are short and clear in the JSON.
- config.json write safety: read -> parse -> mutate -> write back as a single atomic operation. Preserve key ordering (`defaults`, `repos`, `bundles`). Preserve `_`-prefixed metadata keys (e.g. `_include_types_ref`). Use `indent=2` with a trailing newline.
- Never write inside `upstream/<repo>/`.
- Run each Bash invocation as a separate tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`.
