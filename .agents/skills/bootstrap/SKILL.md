---
name: bootstrap
description: Clone any missing Mattermost repos into upstream/. Idempotent.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Read `"$PROJECT_ROOT/.agents/config/repos.json"`'s `repos` array: each entry has `name`, `url`, and
optionally `cbm_excluded`/`cbm_excluded_reason`. Clone every entry under `upstream/<name>/`:

1. If `upstream/<name>/` already exists, skip and report `already present`.
2. Otherwise run `git clone <url> upstream/<name>` and report `cloned` or the git error.

Continue on errors; collect failures and surface them at the end.

Ensure important working directories exist: `mkdir -p upstream tickets`.

Report a Markdown table: `Repo | Result`, where `Result` is `already present`, `cloned`, or the git error.
After the table, one line per cloned/present entry with `cbm_excluded: true`:
`<name>: excluded from codebase-memory indexing (<cbm_excluded_reason>).`

Notes:
- This command does NOT pull or switch. Use `/git-pull` or `/git-switch <repo> <ref>` (pin to tag/branch).
- `.agents/config/repos.json` is the canonical repo list. `AGENTS.md` and `README.md` reference it by name
  rather than duplicating URLs; add a new repo there, not here.
- `cbm_excluded` entries (e.g. `enterprise`) still clone normally; only `/cbm-index-repository` skips
  indexing them. Add a new exclusion by setting both fields on that entry, no skill file changes needed.
