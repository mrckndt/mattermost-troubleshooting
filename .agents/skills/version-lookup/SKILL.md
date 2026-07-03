---
name: version-lookup
description: Resolve a version query (latest esr / latest / X.Y / X.Y.Z / main) to a concrete git ref for an upstream/ repo. Self-refreshes tags/docs before resolving.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `[<repo>] <query>`. Determine `<repo>` by checking whether the first token matches an existing `upstream/<token>/` directory:
- If it matches, that token is `<repo>` and the remaining tokens form `<query>`.
- Otherwise, `<repo>` defaults to `mattermost` and the entire argument string is `<query>` (covers a multi-word query like `latest esr` given with no repo).
  - If the first token also fails to look like part of a query (not `latest`, `esr`, `main`,
    `default`, `release`, and not a bare `X.Y`/`X.Y.Z`/`vX.Y.Z`/`release-X.Y` shape), it was
    likely meant as a repo name. Prepend this note to the output, then resolve as usual:
    `Note: "<first token>" is not a repo under upstream/ - resolving the full string as a query against "mattermost". Run /bootstrap if you expected this repo to exist.`

This skill only resolves a query to a ref; it does not switch. Pass the result to `/git-switch <repo> <ref>`.

## Resolution

Match `<query>` against these forms, in order:

**`latest esr` / `esr`:**
1. Self-refresh the source: `/git-pull docs` (finds the current ESR tag *name*).
2. `grep -m1 "Extended Support Release (ESR)" "$PROJECT_ROOT/upstream/docs/source/product-overview/version-archive.rst" | grep -o 'v[0-9]*\.[0-9]*\.[0-9]*'`
3. Fallbacks if no match, same directory, in order: `common-esr-support-rst.rst`, then `release-policy.md`.
4. Self-refresh the target: `/git-pull <repo>` (fetches the resolved tag into `upstream/<repo>` so the switch does not fail on a missing ref).
5. Result kind: tag. Applies to both `mattermost` and `enterprise` regardless of which repo was passed; note this in the output.

**`latest` / `latest release`:**
1. Self-refresh: `/git-pull <repo>`.
2. ```
   git -C "$PROJECT_ROOT/upstream/<repo>" tag -l 'v*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1
   ```
3. Result kind: tag.

**Exact or minor version (`X.Y` or `X.Y.Z`, no `v`/`release-` prefix):**
- Pure normalization, no lookup or refresh:
  - `X.Y` -> `release-X.Y` (branch)
  - `X.Y.Z` -> `vX.Y.Z` (tag)

**`main` / `default`:**
1. `git -C "$PROJECT_ROOT/upstream/<repo>" symbolic-ref refs/remotes/origin/HEAD --short` (strip the `origin/` prefix).
2. Result kind: branch.

If `<query>` matches none of the above, treat it as already a concrete ref (tag, branch, or sha) and return it unresolved with kind `literal`.

## Output

```
Resolved "<query>" -> <ref> (<tag|branch|literal>, source: <version-archive.rst | git tags | normalized | origin/HEAD>)
```

For `latest esr`, append: `Applies to mattermost and enterprise.`
