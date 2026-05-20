# mattermost-troubleshooting

Workspace for the Claude-Code-driven Mattermost Technical Support Engineer agent. Local clones of upstream Mattermost repos, curated per-repo CLAUDE.md fragments, and on-disk knowledge graphs built with [graphify](https://graphify.net/).

> New to graphify? Start with [Graphify: turn any folder into a knowledge graph](https://openclawapi.org/en/blog/2026-04-12-graphify-knowledge-graph) for the conceptual intro, then [graphify CLI commands](https://graphify.net/graphify-cli-commands.html) for the operational reference.

## Layout

```
.
├── CLAUDE.md                # Top-level agent instructions
├── claude-md/               # Per-upstream-repo CLAUDE.md fragments (imported by CLAUDE.md)
├── upstream/                # Local clones, one directory per upstream repo
├── graphs/                  # Knowledge-graph outputs (gitignored except graphs/config.json)
│   ├── config.json          # repo scopes + bundle definitions
│   ├── <repo>/              # per-repo graph
│   └── _bundles/<name>/     # named cross-repo bundle (e.g. calls)
├── tickets/                 # One subfolder per ticket or investigation (e.g. tickets/12345/, tickets/customer-name/)
└── .claude/
    ├── commands/            # /bootstrap, /git-pull, /git-switch, /graphify-update, /draft-reply, /kb-article, /feature-request, /clipboard
    ├── helpers/             # Workaround scripts (see Active workarounds at the bottom)
    └── settings.local.json  # Project-level Claude Code settings file, mainly containing allowed tools
```

## First-time setup

### Install graphify

Graphify ([graphify.net](https://graphify.net/), [CLI reference](https://graphify.net/graphify-cli-commands.html)) builds the knowledge graphs under `graphs/`. Install before running `/bootstrap --build-graphs`.

Requires Python 3.10 or newer. Recommended: install with `[all]` for full extraction support:

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

Pick a leaner install with `pipx install "graphifyy[gemini,pdf]"` etc. To add an extra to an existing install: `pipx inject graphifyy 'graphifyy[<extra>]'`.

**macOS** - use `pipx` (recent macOS Pythons are externally managed and reject plain `pip install`):

```
brew install pipx && pipx ensurepath
pipx install "graphifyy[all]" && graphify install
```

**Linux / Windows:**

```
pip install "graphifyy[all]" && graphify install
```

Verify: `graphify --help` should print usage. To update: `pipx upgrade graphifyy && graphify install` (or `pip install --upgrade graphifyy && graphify install` on Linux/Windows).

### Graphify build cost and model choice

Graphify's build pipeline has two extraction phases:

- **AST extraction** (code files): deterministic parsing, no LLM calls, cached after the first run. Incremental updates (`/graphify-update`) that touch only code are essentially free.
- **Semantic extraction** (doc/paper/image files): one LLM call per ~22-file chunk. This is where cost accumulates, and the backend matters.

**Gemini Flash is the preferred extraction backend.** `/bootstrap` checks for `GEMINI_API_KEY` or `GOOGLE_API_KEY` and routes semantic extraction through Gemini when either key is set, saving significant tokens compared to Claude subagents. Without a key the pipeline falls back to Claude subagents.

Set the key via shell init or the project secrets file:

- **Shell init** (recommended): `export GEMINI_API_KEY=<your-key>` in `~/.zshrc` or `~/.zshenv`. Claude Code inherits the env from the launching shell.
- **`.claude/secrets.env`** (project-scoped, gitignored): one `KEY=value` per line. The slash commands source this file automatically so Python subprocesses inherit the key.

**Model choice:**

| Use case | Recommended | Notes |
|---|---|---|
| Initial build or full rebuild | Gemini Flash (preferred); Sonnet 4.6 at lower effort | Semantic extraction is structured data output - Gemini Flash is fastest and cheapest. Consider low effort for Sonnet to reduce cost. |
| Incremental update (code only) | Any model | AST extraction only - no LLM calls, essentially free. |
| Working on files in this repo | Sonnet 4.6 (1M context) at high effort | Handles complex troubleshooting notes and cross-file analysis well. Opus also works but is not necessary. |
| Ticket troubleshooting | Opus 4.7 at high effort | High-stakes reasoning across logs, code, and customer context. Sonnet is a reasonable fallback if Opus quota is tight. |

### Clone and start

```
git clone git@github.com:mrckndt/mattermost-troubleshooting.git
cd mattermost-troubleshooting
claude
```

Then inside Claude:
- `/bootstrap` - clone all upstream repos under `upstream/` and create `tickets/`. By default it prompts whether to build any graphify graphs; pick `calls` for the initial Calls bundle (six repos), `all` for everything, or `skip` to defer.

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

- **`/graphify-update`** - incrementally refresh graphs without a git operation.
  - `/graphify-update` - update every built per-repo graph, then cascade bundles.
  - `/graphify-update <repo>` - update one repo and cascade to its bundles.
  - `/graphify-update <bundle-name>` - re-merge + re-cluster + re-label one bundle from existing per-repo graphs.

The agent picks which graph to query automatically every turn - see "Scopes & bundles" below for the model and `CLAUDE.md` "Scope selection" for the algorithm.

### Output (customer-facing artifacts)

- **`/draft-reply [description]`** - draft a customer reply (email, Zendesk, hub thread) from the current troubleshooting context. Optional arg: problem/solution hint.
- **`/kb-article [description]`** - generate a KB article (Markdown + HTML) from the current troubleshooting context. Optional arg: problem/solution hint.
- **`/feature-request [title]`** - generate a structured feature-request post (for PMs) from the current troubleshooting context. Optional arg: feature title or description.
- **`/clipboard [content or description]`** - copy content to the OS clipboard via the platform-appropriate CLI (`pbcopy` / `Set-Clipboard` / `wl-copy`). With no arg, copies the most recent generated artifact.

> Note: `/bootstrap`, `/git-pull`, `/git-switch`, and `/graphify-update` all begin by `cd`-ing the shell to the project root if it isn't already there. A previous skill or tool may have left the shell in a subdirectory; relative paths like `upstream/<repo>` or `graphs/<scope>` would silently misroute. The check uses the `pwd` value plus the presence of the tracked top-level entries (`CLAUDE.md`, `README.md`, `.gitignore`, `.claude/`, `claude-md/`, `upstream/`, `graphs/`).

## Scopes & bundles

Two kinds of graph scope:

| Scope | Path | Contents |
|---|---|---|
| Per-repo | `graphs/<repo>/graphify-out/graph.json` | One upstream repo, nodes for files/functions/types/concepts and edges for imports, calls, references, semantic similarity. |
| Bundle | `graphs/_bundles/<name>/graphify-out/graph.json` | Named cross-repo group merged from two or more per-repo graphs (e.g. the Calls pipeline, the AI stack). |

When no scope auto-selects, the agent falls through to `grep` + the Read tool on `upstream/<repo>/` and says so in the answer.

**Source of truth: `graphs/config.json`.** Repo scope (`full` vs `subdirs`), per-repo `include_types` filters, and every bundle definition live here. Reproduce any scope with `/bootstrap --build-graphs <selector>`.

A bundle definition contains only `repos`:

```json
"bundles": {
  "calls": {
    "repos": ["mattermost", "mattermost-plugin-calls", "rtcd",
              "calls-offloader", "calls-recorder", "calls-transcriber"]
  }
}
```

Keyword-based scope routing is per-repo, not per-bundle. Each repo carries a `keywords` array that the agent matches against question terms; the bundle is then selected by membership. Example:

```json
"repos": {
  "rtcd": { "scope": "full", "keywords": ["rtcd", "RTC", "ICE", "TURN", "STUN"] },
  "enterprise": { "scope": "full", "keywords": ["ldap", "saml", "high availability", "cluster"] }
}
```

**Slash commands:**
- `/bootstrap --build-graphs <bundle-name>` builds missing per-repo graphs then merges them into the bundle. Idempotent.
- `/graphify-update <bundle-name>` re-merges a bundle from existing per-repo graphs.

The agent always queries the `server` bundle first (the foundation under almost every TSE ticket), then routes to additional bundles or per-repo scopes based on the question's keywords. See `CLAUDE.md` "Scope selection" for the full algorithm.

### Why some repos are split into subdirs

Graphify enforces a 2,000,000-word hard cap (above this, a build is rejected) and a 200-file soft warning. Repos over the hard cap need `scope: "subdirs"` in `graphs/config.json`:

- `mattermost` - 7.5M words / 8,022 files
- `docs` - 8.6M words / 482 files
- `mattermost-mobile` - 2.7M words / 2,962 files
- `mattermost-developer-documentation` - 2.4M words / 274 files

`scope: "subdirs"` runs the pipeline once per listed subdir path, each producing its own graph, then merges them into a single `graphs/<repo>/graphify-out/graph.json`. Currently only `mattermost` is split.

### How graph merging works

Graphs merge bottom-up:

1. **Per-subdir to per-repo** (subdirs-scoped repos only): after all subdirs build, slash commands run the merge helper, `graphify cluster-only`, then community labeling. Result: `graphs/<repo>/graphify-out/graph.json`.
2. **Per-repo to bundle**: when any bundle member finishes building, the cascade re-runs the merge helper over all member graphs, then cluster-only, then community labeling.

Operational notes:
- Re-clustering after every merge is fast (seconds, no LLM calls).
- Community labeling is a one-time LLM cost per scope per cascade; labels persist to `.graphify_labels.json`.
- The cascade is automatic via `/git-pull`, `/git-switch`, and `/graphify-update`. Use `/graphify-update <bundle-name>` to repair a stale bundle manually.
- All four cascade commands invoke `.claude/helpers/merge-graphs.py` rather than `graphify merge-graphs` directly (active workaround - see below).

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
5. The agent picks the graph scope automatically every turn. It queries `graphs/_bundles/server/` first, then any additional bundles or per-repo scopes that the question's keywords route to. Customer logs that mention `focalboard` route to the boards plugin scope; mentions of `rtcd` route to the calls bundle. When nothing matches, the agent falls through to grep + the Read tool on `upstream/<repo>/` and says so in the answer.
6. Reference ticket files in your prompt (e.g. `@tickets/12345/mattermost.log`) or just describe the issue - the agent looks under `./tickets/` by default.
7. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - publish a KB article.
   - `/feature-request` - file a PM-facing request.

## Pre-graphify state

The `claude-md/<repo>.md` files on this branch are header-only stubs. The prior TSE notes live at commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe) (the last state before the graphify integration) and are being re-curated incrementally, trimmed to what graphs and docs cannot reproduce: misleading log signatures, license-tier traps, customer-misunderstanding decoders, version-specific gotchas.

## TODO

- [ ] Reconsider adding the `docs` repo back to graphify bundles. See `notes/docs-repo-in-bundles-deferred.md` for the rationale (Tier 1.5 grep replaces docs-in-bundle for TSE work; the docs subgraph has zero cross-edges to code) and the conditions under which it would be worth revisiting.
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
- [ ] Implement an end-to-end ticket-troubleshooting flow the agent runs on request (e.g. a `/triage <ticket-id>` skill): extract the support packet, read the logs / config, let auto-select route to the right graph scope, query for likely causes, save running findings to `tickets/<id>/analysis.md`, and stage the customer artifact via `/draft-reply` or `/kb-article` when the user is ready.

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
