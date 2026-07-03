---
name: git-switch
description: Switch a cloned repo under upstream/ to a tag, branch, or version query like "latest esr" (no ref = default branch)
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Parse args as `<repo> [<ref>]`. Switch `upstream/<repo>` to `<ref>`, or the default branch if `<ref>` is omitted.
`<ref>` may be a literal git ref (tag, branch, sha) or a version query: `latest esr`, `esr`, `latest`, `latest release`, `main`, `default`, or a bare `X.Y`/`X.Y.Z` with no `v`/`release-` prefix.

Steps:

1. Verify `upstream/<repo>/` exists.
   - If not, and the full `$ARGUMENTS` string looks like a ref or query rather than a repo name: stop and report that `<repo>` is missing, not that the repo name is invalid.
     Matches: the version-query list above, or a literal `vX.Y.Z` tag, `release-X.Y` branch, or bare `X.Y`/`X.Y.Z`.
   - Report format: `"<args>" looks like a version query, not a repo. /git-switch requires <repo> first, e.g. /git-switch <repo> <args>.` Do not guess which repo.
   - Otherwise (no match either - a genuine typo): list available repos and stop.
2. Capture the pre-switch HEAD sha: `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse HEAD`.
3. `git -C "$PROJECT_ROOT/upstream/<repo>" status -s`. Do this before any resolution below - never fetch or pull into a dirty repo.
   - If non-empty: report the listed lines as changes about to be discarded.
   - Discard them: `git -C "$PROJECT_ROOT/upstream/<repo>" reset --hard`, then `git -C "$PROJECT_ROOT/upstream/<repo>" clean -fd`.
   - Continue to the next step once clean.
4. Resolve a symbolic `<ref>` before switching:
   - If `<ref>` matches a version query from the list above, run `/version-lookup <repo> <ref>` inline and use the resolved ref below.
   - `latest esr` resolves to a tag shared by `mattermost` and `enterprise`; to switch both, run this skill once per repo with the same query.
5. Switch:
   - If `<ref>` is empty: resolve the default branch via `git -C "$PROJECT_ROOT/upstream/<repo>" symbolic-ref refs/remotes/origin/HEAD --short` (strip `origin/` prefix), then `git switch <default>`.
   - If `<repo>` is `mattermost` or `enterprise` and `<ref>` matches `^v[0-9]+\.[0-9]+\.[0-9]+$` (their patch-tag shape): it is a tag.
     Switch directly with `git switch --detach <ref>`; if that fails (not yet fetched), `fetch --tags --prune` once then retry.
   - If `<repo>` is `mattermost` or `enterprise` and `<ref>` matches `^release-[0-9]+\.[0-9]+$` or is `master`/`main`: it is a branch.
     Switch directly with `git switch <ref>`; if that fails, `fetch --tags --prune` once then retry.
     This shape rule is confirmed for `mattermost`/`enterprise` only (surveyed across `upstream/*`; other repos use incompatible tag/branch shapes) - do not apply it to any other repo.
   - Otherwise (any other repo, or a shape matching neither pattern - rc tags, arbitrary branches, shas): kind is ambiguous.
     (a) `git switch <ref>`; (b) if that fails, `git switch --detach <ref>`; (c) if both fail, `fetch --tags --prune` once then repeat (a) and (b). Do not pre-check whether the ref is a tag.
6. Report by reformatting `git switch`'s own output with the repo path prepended. Prefix `Switched upstream/<repo> to ...`, preserving the rest verbatim. Examples:
   - `Switched to branch 'master'` → `Switched upstream/mattermost to branch 'master'`.
   - `Switched to a new branch 'release-11.5'` → `Switched upstream/mattermost to a new branch 'release-11.5'`.
   - For a detached tag (`HEAD is now at <sha> ...`): `Switched upstream/<repo> to detached HEAD on tag 'v10.5.1' (<sha>)`.
   - If step 3 discarded changes, prefix this line with `Discarded uncommitted changes, then `, e.g. `Discarded uncommitted changes, then switched upstream/mattermost to branch 'master'.`
   Do NOT call `describe --tags --always` or any other extra git command.

Do NOT auto-revert at the end of the turn. Leave the repo on the chosen ref for follow-up reads.
