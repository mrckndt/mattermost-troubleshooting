---
name: cbm-get-architecture
description: Get a high-level architecture overview (packages, services, dependencies, clusters) of a codebase-memory-indexed repo or a subdirectory within it. Wraps get_architecture.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] [<path>]`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and any remaining text is `<path>`, scoping the overview to a subdirectory/package.
- Otherwise, `<repo>` defaults to `mattermost` and any remaining text is `<path>`.

1. Run `/cbm-index-repository <repo>` inline. If it reports `codebase-memory MCP not present`, report the same and stop. Use the `Project` column from its output table as `project` below.
2. Call `get_architecture` with `project` (optionally `aspects` to restrict which sections come back).
   - The tool has no `path` parameter, so scoping happens client-side (step 3).
3. If `<path>` was given, filter client-side:
   - `file_tree` entries whose `path` starts with `<path>`.
   - `entry_points` entries whose `file` starts with `<path>`.
   - `hotspots` entries have no `file` field, only `qualified_name` (`<project>.<dotted-path>.<name>`) - match by checking it contains `.<path-with-slashes-replaced-by-dots>.`.
   - State plainly that `packages`, `clusters`, `routes`, and the `node_labels`/`edge_types` counts are always whole-project; the tool can't scope those.
4. Present the packages/services, dependencies, and `clusters` found.
   - `clusters` come from Leiden community detection over the call/import graph: the de-facto modules (label, member count, cohesion score, representative `top_nodes`, binding packages/edge_types).
   - These often cut across the folder layout and surface real architectural seams the directory structure hides.
