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

Graphify ([graphify.net](https://graphify.net/), [CLI reference](https://graphify.net/graphify-cli-commands.html)) builds the knowledge graphs under `graphs/`. Install before running `/graphify-build`. Requires Python 3.10 or newer.

**macOS** (recent macOS Pythons are externally managed; use pipx):

```
brew install pipx && pipx ensurepath
pipx install graphifyy && graphify install
```

**Linux / Windows:**

```
pip install graphifyy && graphify install
```

Verify with `graphify --help`. To upgrade:

```
pipx upgrade graphifyy && graphify install
```

On Linux / Windows (without pipx):

```
pip install --upgrade graphifyy && graphify install
```

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

### Graphify build cost and model choice

Two LLM cost phases:

- **Semantic extraction** (doc/image files): only in `/graphify-build`. Cost scales with the number of non-code files. Code-only repos pay nothing here.
- **Community labeling**: in both `/graphify-build` and `/graphify-update` after every re-cluster. Cost scales with graph size; large repos run labeling in parallel subagents and this dominates the cost of an incremental update.

**Model choice:**

| Use case | Recommended | Notes |
|---|---|---|
| Full (re)build (`/graphify-build`) | Sonnet 4.6 auto mode, low effort; Gemini Flash (see below) | Labeling subagents don't need deep reasoning - low effort keeps cost down. Gemini Flash is faster and cheaper if you have an API key. |
| AST update (`/graphify-update`) | Sonnet 4.6 auto mode, low effort; Gemini Flash (see below) | AST extract is free; cost comes from community re-labeling subagents. |
| Working on files in this repo | Sonnet 4.6 (1M context) high effort; Opus 4.7 for deeper reasoning | Sonnet 1M handles complex notes and cross-file analysis well. |
| Ticket troubleshooting | Opus 4.7 at high effort | Best for high-stakes reasoning across logs, code, and customer context. Sonnet is a reasonable fallback. |

### Gemini API key (optional)

Gemini Flash can replace Claude subagents for graph builds and updates, reducing cost and build time. Without it, slash commands use Claude subagents automatically.

Add the `gemini` extra:

```
pipx inject graphifyy 'graphifyy[gemini]'
```

Then set the key via:

- **Shell init** (recommended): `export GEMINI_API_KEY=<your-key>` in `~/.zshrc` or `~/.zshenv`.
- **`.claude/secrets.env`** (project-scoped, gitignored): one `KEY=value` per line; slash commands source this automatically.

Both `GEMINI_API_KEY` and `GOOGLE_API_KEY` are recognized.

### Clone and start

```
git clone git@github.com:mrckndt/mattermost-troubleshooting.git
cd mattermost-troubleshooting
claude
```

Then inside Claude:
- `/bootstrap` - clone all upstream repos under `upstream/` and create the working directories. Run `/graphify-build` afterwards to build knowledge graphs.

## Working a ticket

1. Create a folder under `tickets/` for the ticket:
   ```
   mkdir -p tickets/12345
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
4. If the customer's server is on a specific version, pin the repo first (`/git-switch mattermost v10.5.1`). The switch is git-only - run `/graphify-update mattermost` (code-only) or `/graphify-build mattermost` (full rebuild) if you need the knowledge graph aligned to that ref too.
5. Reference ticket files in your prompt (`@tickets/12345/mattermost.log`) or describe the issue - the agent checks `./tickets/` by default. Graph scope is selected automatically; see Scopes & bundles for the routing algorithm.
6. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - publish a KB article.
   - `/feature-request` - file a PM-facing request.

## Slash commands

### Repo management

| Command | What it does |
|---|---|
| `/bootstrap` | Clone missing upstream repos; create working directories. Idempotent. |
| `/git-pull [<repo>]` | `git pull --ff-only`. No arg = all repos; `<repo>` = one repo. Run `/graphify-update` or `/graphify-build` afterwards if HEAD moved. |
| `/git-switch <repo> [<ref>]` | Switch to a tag, branch, or commit. No ref = default branch. Fetches `--tags --prune` as a fallback if the ref is unknown locally. Run a graph refresh after switching. |

### Knowledge graph

| Command | What it does |
|---|---|
| `/graphify-build [<scope>]` | Full pipeline (AST + semantic + cluster + label). Always rebuilds. No arg = prompted; `all` = every repo in config; `<repo>` or `<bundle>` = one scope. Use for initial build, after doc changes, or for a clean slate. |
| `/graphify-update [<scope>]` | Incremental code-only refresh (AST only). No arg = all built repos + cascade bundles; `<repo>` = one repo + cascade; `<bundle>` = re-merge + re-label. Doc/image changes require `/graphify-build`. |

### Output

| Command | What it does |
|---|---|
| `/draft-reply [description]` | Draft a customer reply (email, Zendesk, hub thread) from current troubleshooting context. |
| `/kb-article [description]` | Generate a KB article (Markdown + HTML). |
| `/feature-request [title]` | Generate a structured PM-facing feature-request post. |
| `/clipboard [content]` | Copy to OS clipboard (`pbcopy` / `Set-Clipboard` / `wl-copy`). No arg = most recent artifact. |

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

`/graphify-build <bundle-name>` builds all per-repo graphs in the bundle then merges them. `/graphify-update <bundle-name>` re-merges a bundle from existing per-repo graphs. See `CLAUDE.md` "Scope selection" for the full routing algorithm.

### Why some repos are split into subdirs

Graphify enforces a 2,000,000-word hard cap and a 200-file soft warning. Repos over the cap need `scope: "subdirs"` in `graphs/config.json`:

- `mattermost` - 7.5M words / 8,022 files
- `docs` - 8.6M words / 482 files
- `mattermost-mobile` - 2.7M words / 2,962 files
- `mattermost-developer-documentation` - 2.4M words / 274 files

`scope: "subdirs"` runs the pipeline once per listed subdir, each producing its own graph, then merges them into `graphs/<repo>/graphify-out/graph.json`. Currently only `mattermost` is split.

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
