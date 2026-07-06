# mattermost-troubleshooting

AI agent workspace for Mattermost Technical Support Engineers. Given a ticket, the investigation pipeline pins upstream source to the customer's exact version, searches code, docs, and curated knowledge fragments exhaustively, and produces a root-cause finding with evidence. Output skills generate customer replies, KB articles, and PDE intake posts from the same session.

## Getting started

Setup at a glance:
1. Install CLI tools (`fd`, `rg`).
2. Clone the repo and run `/bootstrap`.
3. (Optional) Enable integrations: enterprise repo access.

### Recommended CLI tools

The agent prefers `fd` and `rg` (ripgrep) over `find` and `grep`. Falls back gracefully if not installed, but these tools are strongly recommended.

**macOS:**
```
brew install fd ripgrep
```

**Linux (Debian/Ubuntu):**
```
apt install fd-find ripgrep
```

**Linux (Red Hat/Fedora):**
```
dnf install fd-find ripgrep
```

**Windows:** Use WSL (Windows Subsystem for Linux) and follow the Linux instructions above. Native Windows is not supported.
```
winget install Microsoft.WSL
```

### GitHub SSH and enterprise repo access

The `enterprise` repo is private. To access it:

1. Add an SSH key to your GitHub account: [Adding a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).
2. Authorize the key for SSO: [Authorizing an SSH key for use with SAML SSO](https://docs.github.com/en/enterprise-cloud@latest/authentication/authenticating-with-single-sign-on/authorizing-an-ssh-key-for-use-with-single-sign-on).

`/bootstrap` will then clone `git@github.com:mattermost/enterprise` alongside the public repos. If SSH auth fails, it reports the error and continues.

### First-time setup

```
git clone git@github.com:mrckndt/mattermost-troubleshooting.git
cd mattermost-troubleshooting
claude
```

Then inside Claude:
```
/bootstrap
```

This clones all upstream repos under `upstream/` and creates the `tickets/` directory. Idempotent - safe to re-run.

> `/bootstrap` and `/git-pull` are mechanical shell operations - a mid-tier model at its default effort/thinking (e.g. **Claude Sonnet 5**) is right for these; no need to manually drop it lower.

### Optional MCP integrations

Set these up after the repo is cloned. The investigation pipeline consults these MCP-backed sources when their tools are available:

- **Mattermost Hub** - the enterprise Claude connector (`mcp__claude_ai_Mattermost_Hub__*`). No local setup; available when your Claude account has the connector enabled.
- **GitHub issues/PRs** - `github.com/mattermost/*`, via the claude.ai GitHub MCP connector; falls back to WebFetch/WebSearch if unavailable.
- **Codebase memory** - a knowledge-graph index of `upstream/<repo>/` clones via [`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp), run locally.

All are optional. When their tools are not present, `/investigate` skips that source with a noted reason and relies on local data (`fragments/`, `upstream/`) plus the GitHub web search. No colleague is blocked for not setting one up.


#### GitHub MCP (custom) setup

Preferred: no Docker service, no PAT to manage.

1. Go to `https://claude.ai/customize/connectors`, add/connect the GitHub connector, and authorize.
2. In Claude Code, run `/mcp` and select the GitHub connector. It registers as `claude.ai GitHub MCP`, tools under `mcp__claude_ai_GitHub_MCP__*`. If a query fails with an org SAML SSO error, disconnect and reconnect via `/mcp` and retry.

This is the pipeline's GitHub source; falls back to WebFetch/WebSearch if unavailable.


#### Codebase memory MCP setup

A local stdio binary.

**macOS:**
```
brew tap deusdata/codebase-memory-mcp https://github.com/DeusData/codebase-memory-mcp
brew install codebase-memory-mcp
```

**Linux (including Windows via WSL):**
```
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config
```

`--skip-config` installs the binary only. Without it, the installer's own `install` subcommand also
runs, registering the MCP under the name `codebase-memory-mcp` (not the `codebase_memory_local` name
this pipeline requires) and writing a global `~/.claude` skill, a Grep/Glob pre-tool hook, and a
SessionStart reminder that duplicate this repo's `cbm-*` skills. Run `codebase-memory-mcp uninstall`
to remove that global config if it was already applied.

Register with Claude Code - the name must be `codebase_memory_local` exactly (the pipeline looks for the `mcp__codebase_memory_local__*` prefix):
```
claude mcp add codebase_memory_local "$(command -v codebase-memory-mcp)"
```
Restart Claude Code so the session loads the tools; verify with `claude mcp list`.

Indexing happens automatically in `/investigate` Phase 5, or manually via `/cbm-index-repository`. Data lives in `~/.cache/codebase-memory-mcp/`; delete that directory to reset.

### Working a ticket

Run all commands from the repo root (`mattermost-troubleshooting/`).

1. Create a folder under `tickets/` for the ticket:
   ```
   mkdir -p tickets/12345
   ```
2. Drop relevant files there (logs, config dumps, support packets, screenshots, etc.):
   ```
   cp ~/Downloads/mattermost.log tickets/12345/
   cp ~/Downloads/support_packet.zip tickets/12345/
   ```
3. Open Claude Code:
   ```
   claude
   ```

   > Default: a **flagship-tier model** (e.g. **Claude Opus 4.8** or an equivalent model) with **1M context** and **high or xhigh effort/thinking** (xhigh sits one step below Claude's "max" tier, reserved for genuinely stuck sessions, not routine use). A **mid-tier model** (e.g. **Claude Sonnet 5**) at high or xhigh effort/thinking is also worth evaluating for `/investigate` itself - not just a cost fallback, potentially faster or a differently-useful result profile. Auto-mode is recommended once the investigation starts - the skill enforces phase order and search completeness regardless of model.

4. Run the investigation pipeline: `/investigate 12345`.

   This command reads every ticket file, pins `mattermost`, `enterprise`, and any in-scope plugin repos to the customer's exact version, then searches exhaustively before forming a hypothesis:
   - Searches source code at four angles (exact error strings, stack trace functions, feature flag and setting key names, symptom keywords) - all required, no skipping.
   - Searches important upgrade notes, the v11 changelog, product docs, developer docs, Mattermost Hub, and GitHub issues per repo - all required.
   - Blocks the hypothesis until all search angles are exhausted and at least two alternatives have been actively disproved.
   - Returns a `file:line` root cause, a Hub/GitHub cross-reference if the issue is known, and writes `tickets/12345/analysis.md` once the investigation concludes, ready for handoffs or a later `/resume`.
5. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - generate a KB article.
   - `/pde-intake` - create a feature request, bug report, or security issue for sharing with PDE Intake Agent.

## Skills / slash commands

Skills under `.agents/skills/` carry `user-invocable: true` and double as Claude Code slash commands via the symlinks in `.claude/commands/`.

### Investigation

- **`/investigate <ticket-ID|ticket-URL|description>`** - the core skill. See the expanded description in "Working a ticket", step 5.

### Output

- **`/draft-reply [description]`** - draft a customer reply (email, Zendesk, hub thread) from the current troubleshooting context.
- **`/kb-article [description]`** - generate a KB article (Markdown + HTML).
- **`/pde-intake [title]`** - generate a structured PD&E intake post (feature request, bug report, or security issue).
- **`/clipboard [content]`** - copy to OS clipboard (`pbcopy` / `Set-Clipboard` / `wl-copy`). No arg = most recent artifact.

### Repo management

- **`/bootstrap`** - clone missing upstream repos and create working directories. Idempotent.

- **`/git-pull [<repo>]`** - `git fetch --tags` then `git pull --ff-only`.
  - No argument: pulls all repos.
  - `<repo>`: pulls one repo.

- **`/git-switch <repo> [<ref>]`** - switch to a tag, branch, commit, or version query.
  - No ref: returns to the default branch.
  - `<ref>`: switches to a tag (e.g. `v10.5.1`), branch, or commit.
  - `<ref>` also accepts a version query (e.g. `latest esr`, `latest`, `11.5`), resolved via `/version-lookup`.

- **`/version-lookup [<repo>] <query>`** - resolve a version query to a concrete git ref.
  - `<repo>`: defaults to `mattermost` when omitted.
  - `<query>`: `latest esr`, `latest`/`latest release`, `X.Y`/`X.Y.Z`, or `main`/`default`.

### Codebase memory

Standalone access to the codebase-memory knowledge graph, usable independently of `/investigate`. `<repo>` defaults to `mattermost` when omitted from any of these.

Each skill name matches the codebase-memory MCP tool it wraps.

- **`/cbm-index-repository [<repo>]`** - reindex a repo into the graph.
  - No argument: reindexes every already-indexed project.
  - `<repo>`: reindexes one repo.

- **`/cbm-search-graph [<repo>] <query>`** - find a symbol or definition by keyword or natural language.
- **`/cbm-search-code [<repo>] <pattern>`** - find a string literal, error message, or config value (graph-augmented grep).
- **`/cbm-trace-path [<repo>] <question or function>`** - trace callers/callees of a function (e.g. "what calls ProcessOrder?").
- **`/cbm-get-code-snippet [<repo>] <name>`** - pull source for a symbol (qualified or short name).
- **`/cbm-query-graph [<repo>] <cypher>`** - run a raw Cypher query for multi-hop or aggregation questions.
- **`/cbm-get-architecture [<repo>] [<path>]`** - get a high-level architecture overview (packages, services, dependencies).
- **`/cbm-detect-changes [<repo>] [<since-ref>]`** - show the blast radius of a diff, risk-classified.

### Ticket management

- **`/resume <ticket-ID>`** - reconstruct context from `analysis.md`, identify the last completed phase, and continue from there.
- **`/search-tickets <keyword>`** - search across all past ticket files and analysis logs; groups results by ticket ID with context snippets.
- **`/fragment-update`** - draft and write fragment updates from the current ticket's Phase 8 findings; presents a diff for approval before writing.
- **`/tldr [ticket-ID|ticket-URL|text]`** - print a concise summary; reads `analysis.md` if present, else runs `/investigate` first. No argument: summarizes the current session's conclusion if one exists.

## Layout

```
.
├── AGENTS.md                # Top-level agent instructions
├── CLAUDE.md                # Claude Code entry point: @-imports AGENTS.md
├── fragments/               # Per-upstream-repo knowledge fragments
├── upstream/                # Local clones, one directory per upstream repo
├── tickets/                 # One subfolder per ticket or investigation (e.g. tickets/12345/, tickets/customer-name/)
├── .agents/
│   └── skills/              # Canonical skill definitions (SKILL.md per skill)
└── .claude/
    ├── commands/            # Symlinks to .agents/skills/*/SKILL.md - required for Claude Code slash command discovery
    └── settings.local.json  # Claude Code-specific: allowed tools and project-level settings
```

## Provider-neutral layout and Claude Code compatibility

The repo uses a provider-neutral layout so it works with any agent framework: `AGENTS.md` for instructions, `.agents/skills/` for skill definitions. Claude Code auto-loads `CLAUDE.md` (not `AGENTS.md`) and discovers slash commands only from `.claude/commands/`. To bridge the gap without duplicating files, `CLAUDE.md` simply `@`-imports `AGENTS.md`, and `.claude/commands/` contains symlinks pointing to the canonical skill files under `.agents/skills/`.

## TODO

- [ ] Revisit `https://github.com/CodeGraphContext/CodeGraphContext` or `ast-grep` if codebase-memory-mcp's indexing approach doesn't pan out (chosen and integrated - see "Codebase memory MCP setup").
- [ ] Add a `/docs-pr` skill: create a feature branch in `upstream/docs`, commit improvements to pages identified during investigation, push, and open a GitHub PR - without leaving the session.
- [ ] Backfill `fragments/<repo>.md` incrementally from commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe), keeping only the irreducible TSE wisdom (misleading log signatures, license-tier traps, customer-misunderstanding decoders, version-specific gotchas).
