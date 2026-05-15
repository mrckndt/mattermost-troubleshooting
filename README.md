# mattermost-troubleshooting

Workspace for the Claude-Code-driven Mattermost Technical Support Engineer agent. Local clones of upstream Mattermost repos, curated per-repo CLAUDE.md fragments, and on-disk knowledge graphs built with [graphify](https://graphify.net/).

> New to graphify? Start with [Graphify: turn any folder into a knowledge graph](https://openclawapi.org/en/blog/2026-04-12-graphify-knowledge-graph) for the conceptual intro, then [graphify CLI commands](https://graphify.net/graphify-cli-commands.html) for the operational reference.

## Layout

```
.
├── CLAUDE.md              # Top-level agent instructions
├── claude-md/             # Per-upstream-repo CLAUDE.md fragments (imported by CLAUDE.md)
├── upstream/              # Local clones, one directory per upstream repo
├── graphs/                # Knowledge-graph outputs (gitignored except graphs/config.json)
│   ├── config.json        # repo scopes + bundle definitions
│   ├── <repo>/            # per-repo graph
│   └── _bundles/<name>/   # named cross-repo bundle (e.g. calls)
├── tickets/               # One subfolder per ticket or investigation (e.g. tickets/12345/, tickets/customer-name/)
└── .claude/
    ├── commands/          # /bootstrap, /git-pull, /git-switch, /graphify-scope, /graphify-update, /graphify-bundle, /draft-reply, /kb-article, /feature-request, /clipboard
    ├── helpers/           # Workaround scripts (see Active workarounds at the bottom)
    └── settings.local.json
```

## Slash commands

### Repo management

- **`/bootstrap`** - clone any missing upstream repos and create `tickets/` if absent. Idempotent.
  - `/bootstrap` - clone only, then prompt before any graphify build.
  - `/bootstrap --build-graphs <bundle-name>` - after cloning, also build the repos listed under that bundle in `graphs/config.json`.
  - `/bootstrap --build-graphs all` - build every repo in `graphs/config.json#/repos`.
  - `/bootstrap --build-graphs <repo>` - build a single repo.

- **`/git-pull [<repo>]`** - `git pull --ff-only` on the current branch.
  - `/git-pull` - pull every repo under `upstream/`.
  - `/git-pull <repo>` - pull just one.
  - Cascade: for every repo whose HEAD moved, runs `graphify update` (AST-only, no LLM calls), re-merges affected bundles, and re-labels their communities.

- **`/git-switch <repo> [<ref>]`** - switch a cloned repo to a tag, branch, or commit.
  - `/git-switch <repo>` - return to the repo's default branch.
  - `/git-switch <repo> <ref>` - switch to a tag (e.g. `v10.5.1`), branch, or commit. Fetches `--tags --prune` only as a fallback if the ref is unknown locally.
  - Cascade: after the switch, runs `graphify update` for the repo, re-merges affected bundles, and re-labels their communities.

### Knowledge graph

- **`/graphify-scope`** - manage which graph subsequent queries target.
  - `/graphify-scope` - list available scopes (per-repo, bundle) and the current pin.
  - `/graphify-scope <scope>` - pin a scope. `<scope>` is a repo name or a bundle name.
  - `/graphify-scope clear` - remove the pin; auto-select resumes (see `CLAUDE.md` for the heuristic).

- **`/graphify-update`** - incrementally refresh graphs without a git operation.
  - `/graphify-update` - update every built per-repo graph, then cascade bundles.
  - `/graphify-update <repo>` - update one repo and cascade to its bundles.
  - `/graphify-update <bundle-name>` - re-merge + re-cluster + re-label one bundle from existing per-repo graphs.

- **`/graphify-bundle`** - manage bundle definitions in `graphs/config.json`. Asks for confirmation before mutating.
  - `/graphify-bundle` - list defined bundles (name, repos, keywords, built status).
  - `/graphify-bundle <name>` - show one bundle's details.
  - `/graphify-bundle add <name> [<repos>] [<keywords>]` - create a bundle. `<repos>` and `<keywords>` are optional comma-separated lists.
  - `/graphify-bundle remove <name>` - delete a bundle from config and remove its built graph (if any).

### Output (customer-facing artifacts)

- **`/draft-reply [description]`** - draft a customer reply (email, Zendesk, hub thread) from the current troubleshooting context. Optional arg: problem/solution hint.
- **`/kb-article [description]`** - generate a KB article (Markdown + HTML) from the current troubleshooting context. Optional arg: problem/solution hint.
- **`/feature-request [title]`** - generate a structured feature-request post (for PMs) from the current troubleshooting context. Optional arg: feature title or description.
- **`/clipboard [content or description]`** - copy content to the OS clipboard via the platform-appropriate CLI (`pbcopy` / `Set-Clipboard` / `wl-copy`). With no arg, copies the most recent generated artifact.

> Note: `/bootstrap`, `/git-pull`, `/git-switch`, `/graphify-scope`, `/graphify-update`, and `/graphify-bundle` all begin by `cd`-ing the shell to the project root if it isn't already there. A previous skill or tool may have left the shell in a subdirectory; relative paths like `upstream/<repo>` or `graphs/<scope>` would silently misroute. The check uses the `pwd` value plus the presence of the tracked top-level entries (`CLAUDE.md`, `README.md`, `.gitignore`, `.claude/`, `claude-md/`, `upstream/`, `graphs/`).

## Scopes & bundles

There are two kinds of graph **scope** the agent can query:

| Scope | Path | Contents |
|---|---|---|
| Per-repo | `graphs/<repo>/graphify-out/graph.json` | One upstream repo, nodes for files/functions/types/concepts and edges for imports, calls, references, semantic similarity. |
| Bundle | `graphs/_bundles/<name>/graphify-out/graph.json` | A **named cross-repo group** of two or more per-repo graphs merged together. Use these for product-level questions that span repos - e.g. the Calls pipeline (`mattermost` ↔ `mattermost-plugin-calls` ↔ `rtcd` ↔ `calls-offloader` ↔ `calls-recorder` ↔ `calls-transcriber`), or the AI stack (`mattermost` ↔ `mattermost-plugin-agents` ↔ `mattermost-plugin-channel-automation`). |

When no scope auto-selects (no repo-name token matches, no bundle keyword matches), the agent falls through to `grep` + the Read tool on `upstream/<repo>/` directly and says so in the answer. There is no `_all` mega-graph; product-level questions go through the matching bundle and cross-cutting research that doesn't fit any bundle goes through grep/upstream.

**Source of truth: `graphs/config.json`.** Repo scope (`full` vs `subdirs`), per-repo `include_types` filters, and every bundle definition (`repos` members + optional `keywords`) live in this single file. It is the only thing under `graphs/` that's tracked in git - all built outputs are `.gitignore`d, so the config plus a `/bootstrap --build-graphs <selector>` is enough for a teammate to reproduce the same scopes.

A bundle definition looks like:

```json
"bundles": {
  "calls": {
    "repos": ["mattermost", "mattermost-plugin-calls", "rtcd",
              "calls-offloader", "calls-recorder", "calls-transcriber"],
    "keywords": ["calls", "rtcd", "recording", "transcription", "RTC", "ICE", "TURN"]
  }
}
```

**How the slash commands connect:**

- `/graphify-bundle` manages the **definitions** in `graphs/config.json` (list, show, `add`, `remove`). It does not build anything; after `add`, run `/bootstrap --build-graphs <bundle-name>` to actually produce the merged graph.
- `/bootstrap --build-graphs <bundle-name>` walks the bundle's `repos` list, builds any per-repo graph that isn't built yet, then merges them into `graphs/_bundles/<bundle-name>/graphify-out/`. Idempotent.
- `/graphify-update <bundle-name>` re-merges and re-clusters the bundle from existing per-repo graphs (use after one of the members was updated).
- `/graphify-scope <scope>` **pins which graph queries hit** for the rest of the session. The argument can be any repo name or any bundle name. When nothing is pinned (the default after `/graphify-scope clear`), the agent **auto-selects** the scope from the question: bundle `keywords` are matched case-insensitively against the question, and a single-word repo-name match also works (e.g. asking about "github" picks `mattermost-plugin-github`). If neither matches, the agent skips the graph layer and answers from grep + upstream/. The exact heuristic lives in `CLAUDE.md` under *Knowledge graphs*.

In short: define bundles in `graphs/config.json` to mirror the products and ticket clusters you handle (or use `/graphify-bundle add` to do it for you), build them with `/bootstrap --build-graphs <name>`, and either pin a scope with `/graphify-scope <name>` for a session or let keyword auto-select route each question.

### Why some repos are split into subdirs

Graphify enforces two size thresholds during `detect`:

- **Hard cap: 2,000,000 words.** Above this, a single-shot build is rejected. The repo *has* to be split.
- **Soft warning: 200 files.** The build still runs, but graphify suggests scoping for predictability and incremental-update speed.

For the Mattermost workspace, the repos over the hard cap are `mattermost` (~7.5M words), `docs` (~8.6M words), `mattermost-mobile` (~2.7M words), and `mattermost-developer-documentation` (~2.4M words). Two more (`mattermost-plugin-boards`, `mattermost-plugin-playbooks`) are large enough that a split is worth considering.

The fix is `scope: "subdirs"` in `graphs/config.json#/repos/<repo>`. Instead of one detect-and-extract pass over the repo root, graphify runs the pipeline **once per listed subdir path**, each producing its own `graphs/<repo>/<subdir-name>/graphify-out/graph.json`. `<subdir-name>` is the relative path with `/` replaced by `_` (e.g. `server/channels/app` → `server_channels_app`). Each per-subdir directory is persistent - kept on disk so `/graphify-update` can refresh only the subdirs whose code actually changed.

Today only `mattermost` is split. Its config entry lists ~20 paths (`api`, `server/public/model`, `server/channels/app`, `webapp/platform`, ...). Each is chosen because it surfaces in TSE tickets and stays under the limits individually; UI-rendering details (`webapp/channels/src/components` at ~3,000 files) and test directories are deliberately omitted.

Individual subdir graphs under `graphs/<repo>/<subdir-name>/` are intermediate artifacts. They're clustered (needed for the subdir-level merge) but **not labeled** - `/graphify-scope` never lists them, users never query them directly, and labeling them would waste tokens. Their `GRAPH_REPORT.md` retains placeholder `Community N` headings by design; the labeled, navigable report is at `graphs/<repo>/graphify-out/GRAPH_REPORT.md`.

### How graph merging works

Graphify graphs compose: any two `graph.json` files can be unioned into a third one. The merge ladder, bottom-up:

1. **Per-subdir → per-repo** (subdir-scoped repos only). After every listed subdir is built, the slash commands run a merge helper (see below), then `graphify cluster-only graphs/<repo>/ --no-viz` to compute community structure on the merged result, then the Community-labeling pass to replace placeholder labels with real names. The top-level `graphs/<repo>/graphify-out/graph.json` is the canonical per-repo graph regardless of whether the repo was built in `full` or `subdirs` mode.
2. **Per-repo → bundle.** When any member of a bundle finishes building, the cascade in `/bootstrap`, `/git-pull`, `/git-switch`, and `/graphify-update` re-runs the merge helper over the bundle's member graphs into `graphs/_bundles/<bundle>/graphify-out/graph.json`, then `cluster-only`, then the Community-labeling pass. Bundles with at least one missing member are skipped (and reported) rather than merged half-built.

Three operational consequences worth knowing:

- **Re-clustering after every merge.** A merge changes the graph's connected components, so community detection is re-run each time. This is fast (seconds) and uses no LLM calls.
- **Re-labeling after every merge.** Communities get plain-language names (e.g. "Authentication Flow", "Calls RTC Loop") via Claude subagents. This is a one-time LLM cost per scope per cascade; the resulting labels persist to `.graphify_labels.json` and are read by `GRAPH_REPORT.md`. See the "Community labeling" section in `.claude/commands/bootstrap.md` for the full block.
- **Cascade is automatic.** You rarely run the merge helper by hand. `/git-pull`, `/git-switch`, and `/graphify-update` decide which bundles intersect the updated repos and re-merge + re-label them. Manual merges (`/graphify-update <bundle-name>`) are there for repairing a stale bundle without touching git.
- **Merge helper.** All four slash commands invoke `.claude/helpers/merge-graphs.py` rather than `graphify merge-graphs` directly, working around an upstream CLI bug. See the **Active workarounds** section at the bottom of this README for details and the path to removing it when upstream lands the fix.

## First-time setup

### Install graphify

Graphify ([graphify.net](https://graphify.net/), [CLI reference](https://graphify.net/graphify-cli-commands.html)) is a Python CLI used to build the knowledge graphs under `graphs/`, and it also ships as an AI coding assistant skill (`graphify install` drops a `/graphify` skill into your assistant's config) so the model can drive build/query/update flows directly. Install it before running `/bootstrap --build-graphs` so the initial graph build can happen. (`/bootstrap` without `--build-graphs` still works without graphify installed; you can install it later and run `/bootstrap --build-graphs <bundle-name>`.)

Requires Python 3.10 or newer.

Recommended: install graphify with **all** optional extras enabled so PDF/office/Gemini/SQL extraction all work out of the box.

```
pipx install "graphifyy[all]" && graphify install
```

What `[all]` bundles:

| Extra | What it adds |
|---|---|
| `pdf` | PDF extraction |
| `office` | `.docx` and `.xlsx` support |
| `google` | Google Sheets rendering |
| `video` | Video/audio transcription (faster-whisper + yt-dlp) |
| `mcp` | MCP stdio server |
| `neo4j` | Neo4j push support |
| `svg` | SVG graph export |
| `leiden` | Leiden community detection (Python < 3.13 only) |
| `ollama` | Ollama local inference |
| `openai` | OpenAI / OpenAI-compatible APIs |
| `gemini` | Google Gemini API |
| `bedrock` | AWS Bedrock (uses IAM, no API key) |
| `sql` | SQL schema extraction |

Pick one extra instead of `[all]` if you want a leaner install: `pipx install "graphifyy[gemini,pdf]"`, etc. Each extra is also installable in isolation via `pip install "graphifyy[<extra>]"`. If graphify is already installed and you want to add an extra without reinstalling: `pipx inject graphifyy 'graphifyy[<extra>]'`.

**macOS** - use `pipx` (recent macOS Pythons are externally managed and reject plain `pip install`):

```
brew install pipx
pipx ensurepath
pipx install "graphifyy[all]" && graphify install
```

`pipx ensurepath` is a one-time, idempotent step that adds `~/.local/bin` to your shell PATH. Skip it if pipx is already on your PATH (re-run is safe but does nothing).

**Linux / Windows** - the one-liner from the graphify docs:

```
pip install "graphifyy[all]" && graphify install
```

Verify: `graphify --help` should print usage.

#### Updating graphify

Update the Python package and the skill separately:

```
pipx upgrade graphifyy   # macOS / pipx
pip install --upgrade graphifyy   # Linux / Windows
graphify install   # refresh the /graphify skill in your assistant config
```

`graphify install` is idempotent - re-running it overwrites the installed skill with the version bundled in the upgraded Python package. Run it whenever you upgrade `graphifyy`.

### Graphify build cost and model choice

Graphify's build pipeline has two extraction phases with very different costs:

- **AST extraction** (code files): deterministic parsing, no LLM calls, cached after the first run. Incremental updates (`/graphify-update`) that touch only code are essentially free.
- **Semantic extraction** (doc/paper/image files): one LLM call per ~22-file chunk. This is where cost accumulates, and the backend matters.

**Gemini Flash is the preferred extraction backend.** `/bootstrap` checks for `GEMINI_API_KEY` or `GOOGLE_API_KEY` and automatically routes semantic extraction through `graphify.llm.extract_corpus_parallel(backend="gemini")` when either key is set, saving significant tokens compared to Claude subagents. The default model is `gemini-3-flash-preview`; override with `GRAPHIFY_GEMINI_MODEL`. Without a key the pipeline falls back to Claude subagents - still works, just more expensive.

Set the key via shell init or the project secrets file:

- **Shell init** (recommended): `export GEMINI_API_KEY=<your-key>` in `~/.zshrc` or `~/.zshenv`. Claude Code inherits the env from the launching shell.
- **`.claude/secrets.env`** (project-scoped, gitignored): one `KEY=value` per line. The slash commands source this file automatically so Python subprocesses inherit the key.

**Model choice for Claude (when no Gemini key, or for TSE work):**

| Use case | Recommended | Why |
|---|---|---|
| Initial build or full rebuild | Gemini Flash (preferred); Sonnet 4.6 (low effort) | Semantic extraction is structured data output - Gemini Flash is fastest and cheapest. If using Sonnet, low effort is recommended: subagents do simple extraction and don't need deep reasoning; save the context budget for TSE work. |
| Incremental update (code only) | Any model | No LLM calls - AST only |
| Operational commands (`/git-pull`, `/bootstrap`, graphify rebuilds and cascades) | Sonnet 4.6 (default effort) | Mostly orchestration and merging - no deep reasoning needed, but the agent still has to make judgment calls about what to rebuild and not invent shell commands. Sonnet at default effort is the sweet spot. |
| TSE troubleshooting sessions | Opus 4.7 at high effort | TSE work is high-stakes reasoning across logs, code, and customer context; the extra capability matters more than per-token cost on a few tickets per day. Sonnet 4.6 is a reasonable fallback if Opus quota is tight. |

**Do not use Opus for graphify builds.** Semantic extraction dispatches tens to hundreds of subagents on a large repo. At Opus pricing this is expensive without any quality gain - the task is structured data extraction, not complex reasoning.

### Clone and start

```
git clone git@github.com:mrckndt/mattermost-troubleshooting.git
cd mattermost-troubleshooting
claude
```

Then inside Claude:
- `/bootstrap` - clone all upstream repos under `upstream/` and create `tickets/`. By default it prompts whether to build any graphify graphs; pick `calls` for the initial Calls bundle (six repos), `all` for everything, or `skip` to defer.

## Working a ticket

1. Create a folder under `tickets/` named after the ticket ID or any other identifier:
   ```
   mkdir -p tickets/12345          # macOS / Linux
   mkdir tickets\12345              # Windows (cmd or PowerShell)
   ```
2. Drop relevant files there (logs, config dumps, support packets, screenshots, etc.):
   ```
   cp ~/Downloads/mattermost.log tickets/12345/
   cp ~/Downloads/support_packet.zip tickets/12345/ && unzip -d tickets/12345/ tickets/12345/support_packet.zip
   ```
3. Open Claude Code from the **repo root**:
   ```
   cd /path/to/mattermost-troubleshooting
   claude
   ```
4. If the customer's server is on a specific version, pin the relevant repo first:
   - `/git-switch mattermost v10.5.1`
   - This also rebuilds or updates the repo's knowledge graph and re-merges affected bundles.
5. Optionally pin the graph scope for the session so the agent always queries the right graph:
   - `/graphify-scope calls` for a Calls ticket.
   - `/graphify-scope <repo>` for a single-repo ticket (e.g. `/graphify-scope mattermost-plugin-github`).
   - `/graphify-scope clear` when you're done.
   - When nothing matches and no scope is pinned, the agent skips the graph layer and answers from grep + the Read tool on `upstream/`.
6. Reference ticket files in your prompt (e.g. `@tickets/12345/mattermost.log`) or just describe the issue - the agent looks under `./tickets/` by default.
7. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - publish a KB article.
   - `/feature-request` - file a PM-facing request.

## Pre-graphify state

The `claude-md/<repo>.md` files on this branch are header-only stubs. The prior TSE notes live at commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe) (the last state before the graphify integration) and are being re-curated incrementally, trimmed to what graphs and docs cannot reproduce: misleading log signatures, license-tier traps, customer-misunderstanding decoders, version-specific gotchas.

## TODO

- [ ] Backfill `claude-md/<repo>.md` incrementally from commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe), keeping only the irreducible TSE wisdom.
- [ ] Define additional bundles in `graphs/config.json` for common products. 
- [ ] Figure out the proper way to include private repos like `enterprise` (clone-time auth, agent visibility, what to commit vs. keep local).
- [ ] Tune `.claude/settings.local.json` so it auto-allows the commands needed for normal workflows here but denies questionable ones - especially relevant in auto mode.
- [ ] Add `scope: subdirs` entries to `graphs/config.json` for any repo too big for a full index. `graphify.detect.detect()` over every repo under `upstream/` (run 2026-05-12) flags four repos over the 2M-word hard cap and two more that warrant a split:
  - [ ] `mattermost-mobile` - 2.7M words / 2,962 files (over hard cap; not in config yet)
  - [ ] `mattermost-developer-documentation` - 2.4M words / 274 files (over hard cap; not in config yet)
  - [ ] `docs` - 8.6M words / 482 files (over hard cap; not in config yet)
  - [x] `mattermost` - 7.5M words / 8,022 files (over hard cap; already scoped in config)
  - [ ] `mattermost-plugin-boards` - 1.1M words / 963 files (under hard cap but large; consider scoping)
  - [ ] `mattermost-plugin-playbooks` - 746K words / 1,055 files (under hard cap but large; consider scoping)
  - Everything else fits a full build; `desktop`, `mattermost-plugin-agents`, `mattermost-plugin-calls`, and `migration-assist` trip the 200-file soft warning but stay well under the word cap.
- [ ] Implement an end-to-end ticket-troubleshooting flow the agent runs on request (e.g. a `/triage <ticket-id>` skill): extract the support packet, read the logs / config, auto-pin the right graph scope, query for likely causes, save running findings to `tickets/<id>/analysis.md`, and stage the customer artifact via `/draft-reply` or `/kb-article` when the user is ready.

## Active workarounds

Local workarounds for known upstream bugs. Each entry has a verification command and exact removal steps for the day the upstream fix lands.

### `graphify merge-graphs` CLI bug

**What:** all four cascade slash commands invoke `.claude/helpers/merge-graphs.py` instead of `graphify merge-graphs`. The helper accepts the same `<inputs...> --out <output>` argument shape as the upstream CLI and produces the same output, but works around a bug in the installed graphify version: `graphify merge-graphs` initialises its accumulator as a plain `Graph` while `prefix_graph_for_global` returns a `MultiGraph`, so `networkx.compose` fails with `All graphs must be graphs or multigraphs.`. The helper uses a `MultiGraph` accumulator and coerces inputs as needed.

**How to check if it's still needed:** run `pipx upgrade graphifyy` (or pin the version that contains the upstream fix), then try a real merge with the bare CLI:

```
graphify merge-graphs graphs/mattermost-plugin-agents/graphify-out/graph.json graphs/mattermost-plugin-channel-automation/graphify-out/graph.json --out /tmp/test.json
```

**How to remove if the bare CLI succeeds:**
1. Delete `.claude/helpers/merge-graphs.py`.
2. Remove `!.claude/helpers/` and `!.claude/helpers/**` from `.gitignore`.
3. In every `.claude/commands/*.md` file, replace every `"$PYTHON" .claude/helpers/merge-graphs.py ...` invocation with plain `graphify merge-graphs ...` (same arguments).
4. Remove the "Workarounds (active)" subsection from `CLAUDE.md` (Knowledge graphs section).
5. Remove this section from the README.

The upstream patch and bug history live in `notes/graphify-merge-graphs-upstream-fix.md`. If you want to push the upstream fix yourself, file a GitHub issue or PR against the graphify repo and reference that note.
