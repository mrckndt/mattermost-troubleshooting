# mattermost-troubleshooting

AI agent workspace for Mattermost Technical Support Engineers. Given a ticket, the investigation pipeline pins upstream source to the customer's exact version, searches code, docs, and curated knowledge fragments exhaustively, and produces a root-cause finding with evidence. Output skills generate customer replies, KB articles, and PDE intake posts from the same session.

## Getting started

Setup at a glance:
1. Install CLI tools (`fd`, `rg`).
2. Clone the repo and run `/bootstrap`.
3. (Optional) Enable integrations: enterprise repo access, Jira MCP.

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

### Optional MCP integrations

Set these up after the repo is cloned (the Jira steps reference files under `mcp/`). The investigation pipeline consults these MCP-backed sources when their tools are available:

- **Mattermost Hub** - the enterprise Claude connector (`mcp__claude_ai_Mattermost_Hub__*`). No local setup; available when your Claude account has the connector enabled.
- **Internal Jira** - `mattermost.atlassian.net` (`MM-XXXXX`) via [`sooperset/mcp-atlassian`](https://github.com/sooperset/mcp-atlassian), run locally.
- **GitHub issues/PRs** - `github.com/mattermost/*`, preferably via the claude.ai GitHub MCP connector; falls back to a local [`github/github-mcp-server`](https://github.com/github/github-mcp-server) instance.
- **Codebase memory** - a knowledge-graph index of `upstream/<repo>/` clones via [`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp), run locally.

All are optional. When their tools are not present, `/investigate` skips that source with a noted reason and relies on local data (`fragments/`, `upstream/`) plus the GitHub web search. No colleague is blocked for not setting one up.

Each Docker-based MCP server (Jira, GitHub) lives in its own folder under `mcp/`, isolating its compose project and `.env`. codebase-memory-mcp is a local stdio binary with no Docker service - see its setup section below.

#### Jira MCP setup

A long-lived docker-compose service (SSE, port `7080`).

1. Create an API token at `https://id.atlassian.com/manage-profile/security/api-tokens` - use **Create API token** (the plain, unscoped one). Read-only is enforced via `READ_ONLY_MODE` in `.env`, not token scopes.

2. Copy the template and fill in credentials (`.env` is gitignored - never commit tokens):
   ```
   cp mcp/atlassian/.env.example mcp/atlassian/.env
   ```
   Set `JIRA_USERNAME` (your email) and `JIRA_API_TOKEN`. `JIRA_URL`, `READ_ONLY_MODE`, and `JIRA_PROJECTS_FILTER` are preset.

3. Start it (re-run after `... pull` to update):
   ```
   docker compose -f mcp/atlassian/docker-compose.yml up -d
   ```

4. Register with Claude Code - the name must be `atlassian_local` exactly (the pipeline looks for the `mcp__atlassian_local__*` prefix, distinct from the remote `claude.ai Atlassian` connector):
   ```
   claude mcp add --transport sse atlassian_local http://localhost:7080/sse
   ```
   Restart Claude Code so the session loads the `jira_*` tools; verify with `claude mcp list`.

#### GitHub MCP (custom) setup

Preferred: no Docker service, no PAT to manage.

1. Go to `https://claude.ai/customize/connectors`, add/connect the GitHub connector, and authorize.
2. In Claude Code, run `/mcp` and select the GitHub connector. It registers as `claude.ai GitHub MCP`, tools under `mcp__claude_ai_GitHub_MCP__*`. If a query fails with an org SAML SSO error, disconnect and reconnect via `/mcp` and retry.

This is the pipeline's preferred GitHub source. The local setup below is a fallback.

#### GitHub MCP (local) setup

A long-lived docker-compose service (streamable HTTP, port `7081`). Kept as a fallback for the GitHub MCP (custom) connector above; may be removed once that connector proves sufficient.

1. Create a classic PAT at `https://github.com/settings/tokens` (GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic) > Generate new token (classic)). Select scopes: `public_repo` (under `repo`), `read:org` (under `admin:org`), `read:user` (under `user`).

   **SAML SSO:** After saving, the token list shows a "Configure SSO" button. You must authorize the token for the `mattermost` org - the org enforces SAML at the API level for all repos, including public ones. Click "Configure SSO" > "Authorize" next to `mattermost`. With `public_repo` scope the token is limited to public repos; use the full `repo` scope instead if you also need private repo access (e.g. `mattermost/enterprise`).

2. Copy the template and fill in credentials (`.env` is gitignored - never commit tokens):
   ```
   cp mcp/github/.env.example mcp/github/.env
   ```
   Set `GITHUB_PERSONAL_ACCESS_TOKEN` to the token value. `GITHUB_READ_ONLY` is preset to `true`.

3. Start it (re-run after `... pull` to update):
   ```
   docker compose -f mcp/github/docker-compose.yml up -d
   ```

4. Register with Claude Code - the name must be `github_local` exactly (the pipeline looks for the `mcp__github_local__*` prefix, distinct from the remote `claude.ai GitHub MCP` connector). Pass the PAT as a Bearer header (`--header` must come after the positional arguments):
   ```
   claude mcp add --transport http github_local http://localhost:7081/ --header "Authorization: Bearer <PAT>"
   ```
   Replace `<PAT>` with the token value from `mcp/github/.env`. Restart Claude Code so the session loads the tools; verify with `claude mcp list`.

#### Codebase memory MCP setup

A local stdio binary.

**macOS:**
```
brew tap "deusdata/codebase-memory-mcp" "https://github.com/DeusData/codebase-memory-mcp"
brew install codebase-memory-mcp
brew trust --formula deusdata/codebase-memory-mcp/codebase-memory-mcp
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

   If the ticket is mirrored to the Mattermost Hub from Zendesk, skip the manual copy: run `/hub-harvest 12345` to fetch the full thread into `tickets/12345/hub-thread.md`.
3. Open Claude Code:
   ```
   claude
   ```

   > Default: a **flagship-tier model** (e.g. **Claude Opus 4.8** or an equivalent model) with **1M context** and **high or xhigh effort/thinking** (xhigh sits one step below Claude's "max" tier, reserved for genuinely stuck sessions, not routine use). A **mid-tier model** (e.g. **Claude Sonnet 5**) at high or xhigh effort/thinking is also worth evaluating for `/investigate` itself - not just a cost fallback, potentially faster or a differently-useful result profile. Auto-mode is recommended once the investigation starts - the skill enforces phase order and search completeness regardless of model.

   > `/bootstrap` and `/git-pull` are mechanical shell operations - a mid-tier model at its default effort/thinking (e.g. **Claude Sonnet 5**) is right for these; no need to manually drop it lower.

4. Run the investigation pipeline: `/investigate 12345`.

   This command reads every ticket file, pins `mattermost`, `enterprise`, and any in-scope plugin repos to the customer's exact version, then searches exhaustively before forming a hypothesis:
   - Searches source code at four angles (exact error strings, stack trace functions, feature flag and setting key names, symptom keywords) - all required, no skipping.
   - Searches important upgrade notes, the v11 changelog, product docs, developer docs, internal Jira, Mattermost Hub, and GitHub issues per repo - all required.
   - Blocks the hypothesis until all search angles are exhausted and at least two alternatives have been actively disproved.
   - Returns a `file:line` root cause, a Hub/GitHub cross-reference if the issue is known, and writes `tickets/12345/analysis.md` once the investigation concludes, ready for handoffs or a later `/resume-investigation`.
5. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article 12345` - generate a KB article scoped to this ticket (saves to `tickets/12345/`).
   - `/pde-intake` - create a feature request, bug report, or security issue for sharing with PDE Intake Agent.

## Skills / slash commands

Skills under `.agents/skills/` carry `user-invocable: true` and double as Claude Code slash commands via the symlinks in `.claude/commands/`.

### Investigation

- **`/hub-harvest <ticket-ID|assignee-email> [time-range]`** - fetch a Zendesk ticket thread from the Mattermost Hub into `tickets/<zd#>/hub-thread.md`, ready for `/investigate`. Given an assignee email instead, harvests every thread assigned to that TSE in the time window (default: last 30 days) and additionally writes an index at `tickets/hub-harvest/<emaillocalpart>-<date>.md`, grouped by status.
- **`/investigate <ticket-ID|ticket-URL|description>`** - the core skill. See the expanded description in "Working a ticket", step 5.

### Output

- **`/draft-reply [description]`** - draft a customer reply (email, Zendesk, hub thread) from the current troubleshooting context.
- **`/kb-article [ticket-ID|description]`** - generate a KB article (Markdown + HTML). Given a ticket ID (or one already active in the session), reads that ticket's `hub-thread.md`/`analysis.md` and saves to `tickets/<ID>/kb-article.md`+`.html`; otherwise saves to `kb-articles/<slug>-<date>.md`+`.html` at the project root.
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
- **`/cbm-detect-changes [<repo>] [<compare-ref>]`** - list symbols defined in a diff's changed files.

### Ticket management

- **`/resume-investigation <ticket-ID>`** - reconstruct context from `analysis.md`/`analysis-full.md` if present, then ask before re-running `/investigate`; runs `/investigate` unprompted only if no prior analysis exists.
- **`/search-tickets <keyword>`** - search across all past ticket files and analysis logs; groups results by ticket ID with context snippets.

## Layout

```
.
├── AGENTS.md                # Top-level agent instructions
├── CLAUDE.md                # Claude Code entry point: @-imports AGENTS.md
├── fragments/               # Per-upstream-repo knowledge fragments
├── mcp/                     # Optional MCP server config, one folder per server (e.g. mcp/atlassian/); .env files gitignored
├── upstream/                # Local clones, one directory per upstream repo
├── tickets/                 # One subfolder per ticket or investigation (e.g. tickets/12345/); tickets/hub-harvest/ holds /hub-harvest assignee-mode indexes
├── kb-articles/             # Standalone KB articles from /kb-article when no ticket is in play
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
- [ ] Figure out how scoped Atlassian API tokens work with the Jira MCP. Scoped tokens currently fail basic auth against the Jira REST endpoints `mcp-atlassian` uses (every query returns empty / `total: -1`), so setup requires an unscoped token. A working scoped-token path would allow least-privilege, per-app credentials.
- [ ] Backfill `fragments/<repo>.md` incrementally from commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe), keeping only the irreducible TSE wisdom (misleading log signatures, license-tier traps, customer-misunderstanding decoders, version-specific gotchas).
- [ ] Remove the local `github-mcp-server` docker-compose setup (`mcp/github/`) once the GitHub MCP (custom) connector has proven reliable as the sole GitHub source.
