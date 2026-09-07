---
name: git-pull
description: Fetch tags and git pull --ff-only for the current branch: one repo (arg) or all repos under upstream/ (no arg). Optional --interval=<name> skips the pull if already done recently enough.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: optionally a single `<repo>` name matching a directory under `upstream/`, and optionally `--interval=<name>`.

- Argument given: verify `upstream/<repo>/` exists (if not, list available repos and stop); process that repo only.
- No argument: process every repo under `upstream/`.
- `--interval=<name>`: gates the pull per repo against `upstream/.last-pull.json` (see below). Omit it for the
  unconditional behavior this skill has always had.

Interval names map to a day-count:

| name | days |
|---|---|
| weekly | 7 |

Add a row here to support another cadence (e.g. `daily` -> `1`, `biweekly` -> `14`, `monthly` -> `30`); nothing
else about the gate logic changes.

For each repo, continue on error and move to the next:

0. If `--interval=<name>` was given: read `"$PROJECT_ROOT/upstream/.last-pull.json"` (treat a missing or
   unparseable file as `{}`). If it has a date for `<repo>`, compute elapsed days:
   `today=$(date +%F)`, then
   `days=$(( ( $(date -j -f "%Y-%m-%d" "$today" +%s) - $(date -j -f "%Y-%m-%d" "$cached" +%s) ) / 86400 ))`.
   If `days` is less than the interval's day-count, skip straight to reporting this repo as
   `skipped (cached, pulled <cached date>)` in the `Pull` column and move to the next repo - do not run steps
   1-4 or step 5 below for it.
1. `git -C "$PROJECT_ROOT/upstream/<repo>" fetch --tags`. Refreshes all tags so a later `/git-switch <tag>` cannot resolve to a stale tag. Runs regardless of branch or detached HEAD.
2. `git -C "$PROJECT_ROOT/upstream/<repo>" status -s`.
   - If non-empty: report the listed lines as changes about to be discarded.
   - Discard them: `git -C "$PROJECT_ROOT/upstream/<repo>" reset --hard`, then `git -C "$PROJECT_ROOT/upstream/<repo>" clean -fd`. Continue once clean.
3. `git -C "$PROJECT_ROOT/upstream/<repo>" pull --ff-only`. Report whatever git says; do not pre-check or guard.
4. `git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD` to capture the branch (`HEAD` = detached, report as `(detached)`).
5. Update `"$PROJECT_ROOT/upstream/.last-pull.json"` with today's date for `<repo>`, read-merge-write so other
   repos' entries survive (create the file if absent). Runs whenever steps 1-4 actually ran, whether or not
   `--interval` was passed - so an explicit unconditional pull also keeps the cache honest.

Report a Markdown table: `Repo | Branch | Pull`.
- `Pull`: `up to date`, `updated <oldsha>..<newsha>`, `skipped (cached, pulled <date>)`, or the git error.

Note: a detached-HEAD repo still fetches tags in step 1 even though its `pull --ff-only` in step 3 reports no upstream branch.
