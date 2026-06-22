# mattermost-troubleshooting

Workspace for the Mattermost Technical Support Engineer agent. Provider-neutral layout (`AGENTS.md`, `.agents/skills/`) with Claude Code as the primary runtime. Local clones of upstream Mattermost repos and curated per-repo knowledge fragments.

## Getting started

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

### Optional CLI tools

`gh` (GitHub CLI) is purely optional - used only for GitHub operations (opening PRs, viewing issues, checks) outside the investigation workflow.

**macOS:**
```
brew install gh
```

**Linux (Debian/Ubuntu):**
```
apt install gh
```

**Linux (Red Hat/Fedora):**
```
dnf install gh
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

> `/bootstrap` and `/git-pull` are mechanical shell operations - prefer Sonnet with minimal thinking to save cost and time.

### Working a ticket

1. Create a folder under `tickets/` for the ticket:
   ```
   mkdir -p tickets/12345
   ```
2. Drop relevant files there (logs, config dumps, support packets, screenshots, etc.):
   ```
   cp ~/Downloads/mattermost.log tickets/12345/
   cp ~/Downloads/support_packet.zip tickets/12345/
   ```
3. Open Claude Code from the repo root:
   ```
   cd /path/to/mattermost-troubleshooting
   claude
   ```
   Set the model to an **Opus-like model** (Opus 4.8 or later) with **1M context** and **>= high thinking effort**. Auto-mode is fine once the investigation starts - the skill enforces phase order and search completeness.

4. Run the investigation pipeline: `/investigate 12345`.
   
   This command reads every ticket file, pins `mattermost`, `enterprise`, and any in-scope plugin repos to the customer's exact version, then searches exhaustively before forming a hypothesis:
   - Searches source code at four angles (exact error strings, stack trace functions, feature flag and setting key names, symptom keywords) - all required, no skipping.
   - Searches important upgrade notes, the v11 changelog, product docs, developer docs, Mattermost Hub, and GitHub issues per repo - all required.
   - Blocks the hypothesis until all search angles are exhausted and at least two alternatives have been actively disproved.
   - Returns a `file:line` root cause, a Hub/GitHub cross-reference if the issue is known, and maintains `tickets/12345/analysis.md` for handoffs and session breaks.
5. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - publish a KB article.
   - `/pde-intake` - file a PM-facing feature request, bug report, or security issue.

## Skills / slash commands

Skills under `.agents/skills/` carry `user-invocable: true` and double as Claude Code slash commands via the symlinks in `.claude/commands/`.

### Investigation

- **`/investigate <ticket-ID|description>`** - the core skill. See the expanded description in "Working a ticket", step 5.

### Repo management

- **`/bootstrap`** - clone missing upstream repos and create working directories. Idempotent.

- **`/git-pull [<repo>]`** - `git pull --ff-only`.
  - No argument: pulls all repos.
  - `<repo>`: pulls one repo.

- **`/git-switch <repo> [<ref>]`** - switch to a tag, branch, or commit.
  - No ref: returns to the default branch.
  - `<ref>`: switches to a tag (e.g. `v10.5.1`), branch, or commit.

### Ticket management

- **`/resume <ticket-ID>`** - reconstruct context from `analysis.md`, identify the last completed phase, and continue from there.
- **`/search-tickets <keyword>`** - search across all past ticket files and analysis logs; groups results by ticket ID with context snippets.
- **`/fragment-update`** - draft and write fragment updates from the current ticket's Phase 8 findings; presents a diff for approval before writing.

### Output

- **`/draft-reply [description]`** - draft a customer reply (email, Zendesk, hub thread) from the current troubleshooting context.
- **`/kb-article [description]`** - generate a KB article (Markdown + HTML).
- **`/pde-intake [title]`** - generate a structured PD&E intake post (feature request, bug report, or security issue).
- **`/clipboard [content]`** - copy to OS clipboard (`pbcopy` / `Set-Clipboard` / `wl-copy`). No arg = most recent artifact.

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

- [ ] Backfill `fragments/<repo>.md` incrementally from commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe), keeping only the irreducible TSE wisdom (misleading log signatures, license-tier traps, customer-misunderstanding decoders, version-specific gotchas).
- [ ] Tune `.claude/settings.local.json` so it auto-allows the commands needed for normal workflows here but denies questionable ones - especially relevant in auto mode.
- [ ] Evaluate persistent codebase memory/graph tooling for faster source lookups: `https://github.com/DeusData/codebase-memory-mcp`, `https://github.com/CodeGraphContext/CodeGraphContext`, or `ast-grep` as alternatives.
- [ ] Update `/feature-request` slash command from the upstream `techsupport-agent` version.
- [ ] Add a `/docs-pr` skill: create a feature branch in `upstream/docs`, commit improvements to pages identified during investigation, push, and open a GitHub PR - without leaving the session.
