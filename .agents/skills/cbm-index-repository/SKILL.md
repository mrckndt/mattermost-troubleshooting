---
name: cbm-index-repository
description: Index one or more upstream/<repo> clones (or every non-excluded repo) into the codebase-memory knowledge graph, skipping any repo whose graph is already current. Wraps index_repository.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: zero, one, or several `<repo>` names matching directories under `upstream/`.

If `mcp__codebase_memory_local__*` is absent: report `codebase-memory MCP not present` and stop.

**Project name**: `mm-<repo>` (e.g. `mm-mattermost`, `mm-rtcd`). Set explicitly via `index_repository`'s
`name` parameter. The `mm-` prefix avoids collisions in the shared `~/.cache/codebase-memory-mcp/` cache
for generically-named repos (`docs`, `docker`, `desktop`).

Read `"$PROJECT_ROOT/.agents/config/repos.json"`'s `repos` array; `excluded` = the set of `name` values
with `cbm_excluded: true`, each carrying a `cbm_excluded_reason`. The file is the source of truth; do
not carry a memorized list (it currently holds more than one name).
**Fail closed:** if this file is missing or fails to parse, stop and report the error. Proceed only with
an `excluded` set read successfully from disk.

Build the target list:
- Args given: exactly those names. Verify each `upstream/<repo>/` exists; for any that doesn't, print
  the `upstream/` directory listing once (so the engineer can spot a typo), drop the name, and note it as
  `<repo>: not found under upstream/`, continuing with the rest.
- No args: every `name` in `repos.json`'s `repos` array. Note any without a clone on disk as
  `<repo>: not cloned, skipped (run /bootstrap)` and drop it.

**De-duplicate the target list, preserving first-seen order, before filtering or probing.** A name given
twice (copy-paste, or overlap between explicit and default args) produces exactly one probe and one
report row, not two.

**Filter the target list against `excluded` before any other step, and run everything below only on the
survivors.** This filter is decided from `repos.json` alone and holds for every argument and phrasing.
For each name in the target list that is also in `excluded`: report
`<repo> excluded from codebase-memory (<cbm_excluded_reason>); use rg/grep against upstream/<repo>/
directly` and drop it. Excluded names reach zero codebase-memory MCP calls and zero CLI calls.

### Freshness gate

For each remaining target repo, run this probe once: one shell call for the worktree facts, one cbm call
for the graph facts, one printed verdict line.

**Step A - worktree facts (no cbm contact).** Prints `<repo> clean=<clean|dirty> head=<iso>`, where
`head` is the newest mtime among the git files that move when the checkout moves.

```
PR="$PROJECT_ROOT"; REPO="<repo>"
R="$PR/upstream/$REPO"
CLEAN=dirty; [ -z "$(git -C "$R" status --porcelain)" ] && CLEAN=clean
SR="$(git -C "$R" symbolic-ref -q HEAD || true)"
REPO="$REPO" CLEAN="$CLEAN" G="$R/.git" SR="$SR" python3 -c '
import os,datetime
g,sr=os.environ["G"],os.environ["SR"]
c=[g+"/HEAD",g+"/logs/HEAD"]
if sr: c.append(g+"/"+sr if os.path.exists(g+"/"+sr) else g+"/packed-refs")
mt=max(os.path.getmtime(f) for f in c if os.path.exists(f))
hm=datetime.datetime.fromtimestamp(mt,datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
print(os.environ["REPO"]+" clean="+os.environ["CLEAN"]+" head="+hm)
'
```

**`.git/HEAD` alone is not enough, and `.git/index` must stay out.**

- Branch-tracked pulls (`git pull --ff-only`) advance the branch ref and append to `.git/logs/HEAD` but
  leave `.git/HEAD` untouched, so a HEAD-only gate misses them. Confirmed on
  `mattermost-plugin-msteams-meetings`: `.git/HEAD` from `2026-04-30`, `logs/HEAD` from `2026-09-03`
  (`pull: Fast-forward`). Detached-HEAD repos (`mattermost`, `desktop`, `mattermost-mobile`) don't have
  this gap since checkout moves `.git/HEAD` itself.
- `.git/index` is excluded: `git status` rewrites its mtime on every call regardless of repo change,
  which would peg `head` to "now" and force a reindex every run.
- `packed-refs` is read only when on a branch with no loose ref file, never when detached - `git fetch
  --tags` can rewrite it without moving the worktree (confirmed on `mattermost-mobile`, detached at
  `v2.43.1`, checkout Aug 31 vs `packed-refs` Sep 3).
- A fetch-only `/git-pull` (no merge) touches only `refs/remotes/*`/`FETCH_HEAD`, neither read here, so it
  correctly still reports `unchanged`.
- This caught 4 of 14 branch-tracking clones with already-stale graphs: `mattermost-operator`,
  `mattermost-plugin-calls`, `mattermost-plugin-jira`, `mattermost-plugin-playbooks`.

**Step B - graph facts.** Call the MCP tool directly. **Never** `codebase-memory-mcp cli`: it cannot run
from inside this skill (see Notes' generation-guard entry).

```
mcp__codebase_memory_local__check_index_coverage
  project:      mm-<repo>
  scopes:       ["."]
  scope_limit:  1
```

`scope_limit: 1` is the parameter's minimum and is what keeps the call cheap: it caps the `entries` array
that would otherwise carry thousands of excluded paths, leaving a response of roughly 700 characters that
still carries both fields the gate reads.

```json
{"project":"mm-mattermost","indexed_at":"2026-09-04T14:09:30Z",
 "metadata":{"index_mode":"full","generation_matches":true}, ...}
```

**Step C - verdict.** Print exactly one line per repo, `<repo> state=<state>` plus ` reason=<...>` on
anything but `unchanged`:

- `error: project not found or not indexed`: `state=reindex reason=not-indexed`. This arrives as a
  tool-level error rather than a normal body; it is still the not-indexed answer, not a probe failure.
- Any other error, or a response without a readable `indexed_at` or `metadata.index_mode`:
  `state=probe-failed reason=<the actual error or missing-field text>`. Never substitute a staleness
  verdict here: a gate that cannot determine freshness says so rather than guessing.
- Otherwise `state=unchanged` when all three hold, else `state=reindex` listing each failing term as
  `dirty`, `mode=<index_mode>`, `stale(idx=<indexed_at><=head=<head>)`:
  - Step A reported `clean`
  - `metadata.index_mode` is `full`
  - `indexed_at` is later than Step A's `head`

### Per-repo steps

Run these in order for each non-excluded target repo.

1. Run the probe above. Record `state`.
2. Capture `ref` = `<REPO_REF>` (see `AGENTS.md` Shell conventions). Same resolution `/git-switch` and
   `/version-lookup` treat as the repo's identity.
3. If `state=unchanged`: skip to the next repo. No `index_repository` call.
4. If `state=probe-failed`: report the line as printed, treat the repo as search-only for the caller
   (`rg --no-ignore --hidden`, or `grep -r`, against `upstream/<repo>/`), and continue to the next repo.
   No `index_repository` or `delete_project` call: freshness is unknown, so neither a rebuild nor a graph
   query is justified on it.
5. If `state=reindex`: call `index_repository` with exactly these arguments.
   - `repo_path`: absolute path to `upstream/<repo>`
   - `name`: `mm-<repo>`
   - `mode`: `full`
   - `persistence`: `false`
6. On `index_repository` error: the tool returns only `index worker ended with exit_nonzero (exit=1,
   signal=0); inspect log: <path>`. Read that log for the real message: skip any leading `level=info`
   line (the log has 1 line some runs, 2 lines others) and report the first substantive line. Leave any
   existing graph in place (a failed worker does not touch it) and continue to the next repo, stopping
   before step 7.
   - `CBM index worker could not start: a pre-coordination or unverified CBM generation is active` (CBM's
     generation guard; see Notes): report `<repo> state=index-blocked reason=<the worker log message
     verbatim>`, leave the repo search-only, and move on. Retry once at most; verified neither
     repo-specific nor transient (identical on four consecutive calls across three repos).
   - Any other worker message: report it verbatim as `state=index-failed reason=<message>`.
7. On success, delete the legacy graph for this repo if one exists. Skipping this leaves two graphs for the
   same repo and wastes the disk the new one just duplicated.
   - Legacy name = absolute repo path, leading `/` stripped, each remaining `/` replaced by `-`
     (e.g. `Users-marco-Mattermost-Repos-mattermost-troubleshooting-upstream-mattermost`).
   - Confirm it exists, then call `delete_project` on that legacy name, which is the only name to pass here.

### Report

A Markdown table: `Repo | Project | State | Ref`. `State` is `reindexed`, `unchanged`, `probe-failed`,
`index-blocked`, or `index-failed`.
- One line per processed repo, from `excluded` in the `index_repository` response on a reindex:
  `Excluded (<repo>): <count> dirs (<comma-joined dirs list>)`. `codebase-memory-mcp` excludes these
  directories from indexing entirely (no results, not "not found"); the other `cbm-*` skills point back
  here when a search unexpectedly comes up empty. Unavailable on a skip; omit the line there.
- One line per policy-excluded repo, per not-cloned repo (`<repo>: not cloned, skipped (run
  /bootstrap)`), and per not-found repo (`<repo>: not found under upstream/`).

### Notes

- **Treat a missing graph as "not indexed yet" and fall back to `rg --no-ignore --hidden` (or `grep -r`).**
  Indexing is on demand, so most cloned repos have no graph at any moment. Absence says nothing about the code.
- **CBM's generation guard blocks the CLI and index workers, not read-only MCP tools.** Both
  `codebase-memory-mcp cli` and `index_repository`'s worker fail identically (`... could not start
  because a pre-coordination or unverified CBM generation is active`; `rc=1`, empty stdout for the CLI),
  which is why Step B never shells out to the CLI and step 6 has `index-blocked`. The trigger isn't
  simply session coexistence (a graph indexed fine alongside six other running `codebase-memory-mcp`
  processes), and `0.10.3` exposes no way to inspect or clear it - don't guess which process holds it or
  ask the engineer to close sessions on that basis. `check_index_coverage`/`list_projects` are unaffected;
  a CLI-based shell probe is what silently produced `reindex` for every repo before this fix. Neither
  behavior is in the CLI's help text.
- `mode: full` indexes `server/public` (the `model`/`client4` module in `mattermost`) along with `i18n`
  and `migrations`; `moderate` and `fast` omit those directories. Changing mode on an indexed repo triggers
  a full rebuild regardless, so `full` is the only mode worth running, and Step C's `index_mode` check
  requires it: a graph built in another mode reports something else and earns a reindex.
- `persistence: false` leaves the working tree and the clone's git config untouched, keeping
  `/git-switch` free to operate. If `upstream/<repo>/.codebase-memory/` ever appears, delete it.
- A reindex rebuilds the whole graph (similarity, semantic edges, search index) at a cost that scales
  with repo size; `mattermost` is a 980 MB graph. Reindex when the gate asks for it.
- **`auto_watch` reindexes in the background after a checkout moves; Step A's mtime comparison sees those
  refreshes and skips the redundant rebuild.** See Step A above for which git files carry that signal and
  why HEAD alone doesn't. The `clean` check separately covers uncommitted edits, which move no git ref.
- **A gate that cannot read the graph reports `probe-failed`, never `reindex`.** Suppressing the error
  (discarded stderr, a swallowed parse failure) turns a broken probe into a confident staleness verdict
  with `idx=None` in it, which reads as a real answer. Keep every diagnostic in the output.
- `list_projects` is the cheap wide sweep for "which graphs exist at all": one compact call returning
  name, root path, branch, node and edge counts. It carries no `indexed_at`, so it cannot answer the
  freshness question and does not replace Step B.
- Indexing is serialized: a no-arg run over every repo processes them one at a time.
- **Two different "excluded" concepts, two different report lines.** `cbm_excluded` in `repos.json` is a
  policy decision (whole repo, never MCP-called): `<repo> excluded from codebase-memory (...)`. The
  `Excluded (<repo>): N dirs` Report line above is a tool limitation inside an already-indexed repo
  (`.git`, `node_modules`, etc.), not a policy choice. Reach for `rg`/`git` against `upstream/<repo>/` in
  both cases.
- This is the manual equivalent of Phase 5 Step 0 in `/investigate`. Every other `cbm-*` skill calls it as
  its presence check, at most once per repo per session.
- For an index that stays wrong after a reindex, call `delete_project` on the project name and index it
  again. Surgical alternative to wiping `~/.cache/codebase-memory-mcp/`.
