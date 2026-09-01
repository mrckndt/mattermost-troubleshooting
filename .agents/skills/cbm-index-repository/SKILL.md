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
with `cbm_excluded: true` (currently `enterprise`; see that entry's `cbm_excluded_reason`).
**Fail closed:** if this file is missing or fails to parse, stop and report the error. Proceed only with
an `excluded` set read successfully from disk.

Build the target list:
- Args given: exactly those names. Verify each `upstream/<repo>/` exists; if one does not, list what is
  under `upstream/` and drop that name, continuing with the rest.
- No args: every `name` in `repos.json`'s `repos` array. Note any without a clone on disk as
  `<repo>: not cloned, skipped (run /bootstrap)` and drop it.

**Filter the target list against `excluded` before any other step, and run everything below only on the
survivors.** This filter is decided from `repos.json` alone and holds for every argument and phrasing.
For each name in the target list that is also in `excluded`: report
`<repo> excluded from codebase-memory (<cbm_excluded_reason>); use rg/grep against upstream/<repo>/
directly` and drop it. Excluded names reach zero codebase-memory MCP calls and zero CLI calls.

### Freshness gate

For each remaining target repo, run this probe once. It prints one line and makes one cbm call.

```
PR="$PROJECT_ROOT"; REPO="<repo>"
CBM="$(command -v codebase-memory-mcp)"
R="$PR/upstream/$REPO"
PROJ="mm-$REPO"
CLEAN=dirty; [ -z "$(git -C "$R" status --porcelain 2>/dev/null)" ] && CLEAN=clean
CV="$("$CBM" cli --json check_index_coverage "{\"project\":\"$PROJ\",\"paths\":[\".\"]}" 2>/dev/null)"
REPO="$REPO" CLEAN="$CLEAN" HEADF="$R/.git/HEAD" CV="$CV" python3 -c '
import json,os,datetime
try: cv=json.loads(json.loads(os.environ["CV"])["content"][0]["text"])
except Exception: cv={}
repo,clean=os.environ["REPO"],os.environ["CLEAN"]
if cv.get("error"):
    print(repo+" state=reindex reason=not-indexed"); raise SystemExit
ia=cv.get("indexed_at"); mode=cv.get("metadata",{}).get("index_mode")
hm=datetime.datetime.fromtimestamp(os.path.getmtime(os.environ["HEADF"]),datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
fresh=bool(ia) and ia>hm
ok=clean=="clean" and mode=="full" and fresh
why=[]
if clean!="clean": why.append("dirty")
if mode!="full": why.append("mode="+str(mode))
if not fresh: why.append("stale(idx="+str(ia)+"<=head="+hm+")")
print(repo+" state="+("unchanged" if ok else "reindex")+("" if ok else " reason="+",".join(why)))
'
```

Report the probe's single line. Its projection is what keeps the gate cheap: `check_index_coverage`
supplies everything the gate reads, in one call.

### Per-repo steps

Run these in order for each non-excluded target repo.

1. Run the probe above. Record `state`.
2. Capture `ref` = `<REPO_REF>` (see `AGENTS.md` Shell conventions). Same resolution `/git-switch` and
   `/version-lookup` treat as the repo's identity.
3. If `state=unchanged`: do not call `index_repository`. Skip to the next repo.
4. If `state=reindex`: call `index_repository` with exactly these arguments.
   - `repo_path`: absolute path to `upstream/<repo>`
   - `name`: `mm-<repo>`
   - `mode`: `full`
   - `persistence`: `false`
5. On `index_repository` error: note it, leave any existing graph in place, and continue to the next
   repo, stopping before step 6.
6. On success, delete the legacy graph for this repo if one exists. Skipping this leaves two graphs for the
   same repo and wastes the disk the new one just duplicated.
   - Legacy name = absolute repo path, leading `/` stripped, each remaining `/` replaced by `-`
     (e.g. `Users-marco-Mattermost-Repos-mattermost-troubleshooting-upstream-mattermost`).
   - Confirm it exists, then call `delete_project` on that legacy name, which is the only name to pass here.

### Report

A Markdown table: `Repo | Project | State | Ref`.
- One line per processed repo, from `excluded` in the `index_repository` response on a reindex:
  `Excluded (<repo>): <count> dirs (<comma-joined dirs list>)`. `codebase-memory-mcp` excludes these
  directories from indexing entirely (no results, not "not found"); the other `cbm-*` skills point back
  here when a search unexpectedly comes up empty. Unavailable on a skip; omit the line there.
- One line per policy-excluded repo and per not-cloned repo, as worded above.

### Notes

- **Treat a missing graph as "not indexed yet" and fall back to `rg`.** Indexing is on demand, so most
  cloned repos have no graph at any moment. Absence says nothing about the code.
- `mode: full` indexes `server/public` (the `model`/`client4` module in `mattermost`) along with `i18n`
  and `migrations`. `moderate` and `fast` omit those directories, and changing mode on an indexed repo
  triggers a full rebuild regardless, so `full` is the only mode worth running.
- `persistence: false` leaves the working tree and the clone's git config untouched, keeping
  `/git-switch` free to operate. If `upstream/<repo>/.codebase-memory/` ever appears, delete it.
- A reindex rebuilds the whole graph (similarity, semantic edges, search index) at a cost that scales
  with repo size; `mattermost` is a 980 MB graph. Reindex when the gate asks for it.
- **The gate compares the graph's build time to the checkout's last change.** `auto_watch` reindexes in
  the background after a checkout moves, and this comparison sees those refreshes and skips the redundant
  rebuild. Pair it with the `clean` check, which covers uncommitted edits that leave `.git/HEAD` untouched.
- Require `index_mode: full` so the gate accepts only a fully-indexed graph. A graph built in another
  mode reports something else and earns a reindex.
- Indexing is serialized: a no-arg run over every repo processes them one at a time.
- `cbm_excluded` in `repos.json` is a policy decision (private, license-gated repos). The excluded-dirs
  list above is a tool limitation; reach for `rg`/`git` against `upstream/<repo>/` in both cases.
- This is the manual equivalent of Phase 5 Step 0 in `/investigate`. Every other `cbm-*` skill calls it as
  its presence check, at most once per repo per session.
- For an index that stays wrong after a reindex, call `delete_project` on the project name and index it
  again. Surgical alternative to wiping `~/.cache/codebase-memory-mcp/`.
