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
    ├── commands/            # /bootstrap, /git-pull, /git-switch, /graphify-build, /graphify-update, /draft-reply, /kb-article, /feature-request, /clipboard
    ├── helpers/             # Workaround scripts (see Active workarounds at the bottom)
    └── settings.local.json  # Project-level Claude Code settings file, mainly containing allowed tools
```

## First-time setup

### Install graphify

Graphify ([graphify.net](https://graphify.net/), [CLI reference](https://graphify.net/graphify-cli-commands.html)) builds the knowledge graphs under `graphs/`. Install before running `/graphify-build`.

Requires Python 3.10 or newer. Install with `[all]` for full extraction support:

```
pipx install "graphifyy[all]" && graphify install
```

`[all]` bundles:

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

Leaner install: `pipx install "graphifyy[gemini,pdf]"` etc. Add an extra later: `pipx inject graphifyy 'graphifyy[<extra>]'`.

**macOS** - use `pipx` (recent macOS Pythons are externally managed and reject plain `pip install`):

```
brew install pipx && pipx ensurepath
pipx install "graphifyy[all]" && graphify install
```

**Linux / Windows:**

```
pip install "graphifyy[all]" && graphify install
```

Verify: `graphify --help`. Update: `pipx upgrade graphifyy && graphify install` (or `pip install --upgrade graphifyy && graphify install` on Linux/Windows).

### Graphify build cost and model choice

Three pipeline phases, two of them LLM-driven:

- **AST extraction** (code files): deterministic, no LLM, cached. Free.
- **Semantic extraction** (doc/image files): one LLM call per ~22-file chunk. Only runs in `/graphify-build` (full pipeline); `/graphify-update` skips it.
- **Community labeling**: one LLM call per community (or one per ~30-50-community chunk via parallel subagents for large scopes). Runs in both `/graphify-build` and `/graphify-update` whenever the graph is re-clustered. This is typically the dominant cost on incremental updates of large scopes.

**Gemini Flash is the preferred extraction backend.** `/graphify-build` checks for `GEMINI_API_KEY` or `GOOGLE_API_KEY` and routes semantic extraction through Gemini when either is set; falls back to Claude subagents otherwise.

Set the key via:

- **Shell init** (recommended): `export GEMINI_API_KEY=<your-key>` in `~/.zshrc` or `~/.zshenv`.
- **`.claude/secrets.env`** (project-scoped, gitignored): one `KEY=value` per line; slash commands source this automatically.

**Model choice:**

| Use case | Recommended | Notes |
|---|---|---|
| Initial build or full rebuild | Gemini Flash (preferred); Sonnet 4.6 at lower effort | Gemini Flash is fastest and cheapest for structured data output; use low effort for Sonnet to reduce cost. |
| Incremental update (code only) | Gemini Flash for labeling subagents | AST extract is free, but community re-labeling is LLM-driven. Sonnet/Opus only if you want richer labels. |
| Working on files in this repo | Sonnet 4.6 (1M context) at high effort | Handles complex notes and cross-file analysis well. |
| Ticket troubleshooting | Opus 4.7 at high effort | Best for high-stakes reasoning across logs, code, and customer context. Sonnet is a reasonable fallback. |

### Optional CLI tools

The agent prefers `fd` and `rg` (ripgrep) over `find` and `grep` when available. Falls back to the standard tools if they are not installed.

**macOS:**
```
brew install fd ripgrep
```

**Linux (Debian/Ubuntu):**
```
apt install fd-find ripgrep
```

### Clone and start

```
git clone git@github.com:mrckndt/mattermost-troubleshooting.git
cd mattermost-troubleshooting
claude
```

Then inside Claude:
- `/bootstrap` - clone all upstream repos under `upstream/` and create the working directories. Run `/graphify-build` afterwards to build knowledge graphs.

## Slash commands

### Repo management

- **`/bootstrap`** - clone any missing upstream repos and ensure working directories exist. Idempotent. No arguments.

- **`/git-pull [<repo>]`** - `git pull --ff-only` on the current branch. Pure git wrapper; does not touch graphs.
  - `/git-pull` - pull every repo under `upstream/`.
  - `/git-pull <repo>` - pull just one.
  - After a HEAD move, run `/graphify-update <repo>` (code-only, AST + re-label) or `/graphify-build <repo>` (full rebuild, also re-runs semantic extraction) to refresh.

- **`/git-switch <repo> [<ref>]`** - switch a cloned repo to a tag, branch, or commit. Pure git wrapper; does not touch graphs.
  - `/git-switch <repo>` - return to the repo's default branch.
  - `/git-switch <repo> <ref>` - switch to a tag (e.g. `v10.5.1`), branch, or commit. Fetches `--tags --prune` only as a fallback if the ref is unknown locally.
  - After the switch, run `/graphify-update <repo>` or `/graphify-build <repo>` if you need the graph refreshed for that version.

### Knowledge graph

- **`/graphify-build`** - full pipeline (detect + AST + semantic extract + cluster + label). Always rebuilds when invoked - no idempotent skip on existing graphs. Use this for the initial build, after pulling doc/non-code changes, or for a clean slate.
  - `/graphify-build` - prompt for which scope to build.
  - `/graphify-build <bundle-name>` - build the repos in that bundle and merge into a bundle graph.
  - `/graphify-build all` - build every repo in `graphs/config.json#/repos`.
  - `/graphify-build <repo>` - build a single repo.
  - Cost: AST extract (free) + semantic extract (one LLM call per ~22-file chunk; Gemini Flash or Claude subagents) + community labeling (LLM, subagent-batched for large scopes).

- **`/graphify-update`** - incremental code-only refresh (wraps upstream `graphify update`, AST only). Doc/image/paper changes are silently ignored - use `/graphify-build` for those.
  - `/graphify-update` - update every built per-repo graph, then cascade bundles.
  - `/graphify-update <repo>` - update one repo and cascade to its bundles.
  - `/graphify-update <bundle-name>` - re-merge + re-cluster + re-label one bundle from existing per-repo graphs.
  - Cost: AST extract is free, but community re-labeling is still LLM-driven and runs subagents for large scopes. Not zero-cost.

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

When no scope auto-selects, the agent falls through to `grep` + the Read tool on `upstream/<repo>/` and says so.

**Source of truth: `graphs/config.json`.** Repo scope (`full` vs `subdirs`), per-repo `include_types` filters, and bundle definitions all live here. Reproduce any scope with `/graphify-build <selector>`.

A bundle definition contains only `repos`:

```json
"bundles": {
  "calls": {
    "repos": ["mattermost", "mattermost-plugin-calls", "rtcd",
              "calls-offloader", "calls-recorder", "calls-transcriber"]
  }
}
```

Keyword routing is per-repo: each repo carries a `keywords` array matched against the question; the bundle is selected by membership. Example:

```json
"repos": {
  "rtcd": { "scope": "full", "keywords": ["rtcd", "RTC", "ICE", "TURN", "STUN"] },
  "enterprise": { "scope": "full", "keywords": ["ldap", "saml", "high availability", "cluster"] }
}
```

**Slash commands:**
- `/graphify-build <bundle-name>` builds missing per-repo graphs then merges them into the bundle. Idempotent.
- `/graphify-update <bundle-name>` re-merges a bundle from existing per-repo graphs.

The agent queries the `server` bundle first, then routes to additional bundles or per-repo scopes by keyword. See `CLAUDE.md` "Scope selection" for the full algorithm.

### Why some repos are split into subdirs

Graphify enforces a 2,000,000-word hard cap and a 200-file soft warning. Repos over the cap need `scope: "subdirs"` in `graphs/config.json`:

- `mattermost` - 7.5M words / 8,022 files
- `docs` - 8.6M words / 482 files
- `mattermost-mobile` - 2.7M words / 2,962 files
- `mattermost-developer-documentation` - 2.4M words / 274 files

`scope: "subdirs"` runs the pipeline once per listed subdir, each producing its own graph, then merges them into `graphs/<repo>/graphify-out/graph.json`. Currently only `mattermost` is split.

### How graph merging works

Graphs merge bottom-up:

1. **Per-subdir to per-repo** (subdirs-scoped repos only): after all subdirs build, slash commands run the merge helper, `graphify cluster-only`, then community labeling. Result: `graphs/<repo>/graphify-out/graph.json`.
2. **Per-repo to bundle**: when any bundle member finishes building, the cascade re-runs the merge helper over all member graphs, then cluster-only, then community labeling.

Operational notes:
- Re-clustering is fast (seconds, no LLM calls).
- Community labeling is a one-time LLM cost per cascade; labels persist to `.graphify_labels.json`.
- The cascade is triggered manually via `/graphify-update` (code-only) or `/graphify-build` (full). `/git-pull` and `/git-switch` print a hint when graphs may need refresh; they do not run the cascade themselves.
- Both graph-refresh commands (`/graphify-build`, `/graphify-update`) use `.claude/helpers/merge-graphs.py` instead of `graphify merge-graphs` directly (active workaround - see below).

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
4. If the customer's server is on a specific version, pin the repo first (`/git-switch mattermost v10.5.1`). The switch is git-only - if you need the knowledge graph aligned to that ref too, run `/graphify-update mattermost` (code-only) or `/graphify-build mattermost` (full rebuild) afterwards.
5. The agent picks the graph scope automatically. It queries `graphs/_bundles/server/` first, then routes to additional bundles or per-repo scopes by keyword (e.g. `focalboard` routes to boards, `rtcd` to calls). When nothing matches, it falls through to grep + the Read tool and says so in the answer.
6. Reference ticket files in your prompt (e.g. `@tickets/12345/mattermost.log`) or describe the issue - the agent checks `./tickets/` by default.
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

Local workarounds for known upstream bugs, each with a verification command and removal steps.

### `graphify merge-graphs` CLI bug

**What:** all four cascade slash commands use `.claude/helpers/merge-graphs.py` instead of `graphify merge-graphs`. The helper has the same `<inputs...> --out <output>` interface but fixes a bug in the installed version: `graphify merge-graphs` initialises its accumulator as a plain `Graph` while `prefix_graph_for_global` returns a `MultiGraph`, so `networkx.compose` fails with `All graphs must be graphs or multigraphs.`. The helper uses a `MultiGraph` accumulator and coerces inputs as needed.

**Check if still needed:** run `pipx upgrade graphifyy` (or pin the version with the fix), then try a real merge:

```
graphify merge-graphs graphs/mattermost-plugin-agents/graphify-out/graph.json graphs/mattermost-plugin-channel-automation/graphify-out/graph.json --out /tmp/test.json
```

**How to remove if the bare CLI succeeds:**
1. Delete `.claude/helpers/merge-graphs.py`.
2. Remove `!.claude/helpers/` and `!.claude/helpers/**` from `.gitignore`.
3. In every `.claude/commands/*.md` file, replace every `"$PYTHON" .claude/helpers/merge-graphs.py ...` invocation with plain `graphify merge-graphs ...` (same arguments).
4. Remove the "Workarounds (active)" subsection from `CLAUDE.md` (Knowledge graphs section).
5. Remove this section from the README.

The upstream patch and bug history live in `notes/graphify-merge-graphs-upstream-fix.md`; file a GitHub issue or PR against graphify and reference that note to push the fix upstream.
