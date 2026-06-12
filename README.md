# mattermost-troubleshooting

Workspace for the Mattermost Technical Support Engineer agent. Provider-neutral layout (`AGENTS.md`, `.agents/skills/`) with Claude Code as the primary runtime. Local clones of upstream Mattermost repos and curated per-repo knowledge fragments.

## Getting started

### Optional CLI tools

The agent prefers `fd` and `rg` (ripgrep) over `find` and `grep`. Optional - if not installed, `find` and `grep` are used instead.

`gh` (GitHub CLI) is also used by Claude Code for GitHub operations (PRs, issues, checks). Optional.

**macOS:**
```
brew install fd ripgrep gh
```

**Linux (Debian/Ubuntu):**
```
apt install fd-find ripgrep gh
```

**Linux (Red Hat/Fedora):**
```
dnf install fd-find ripgrep gh
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
4. Pin repos to the customer's version if needed: `/git-switch mattermost v10.5.1`.
5. Run the investigation pipeline: `/investigate 12345`. This unpacks any archives, reads all ticket files, infers scope, aligns repos to the customer's version, searches fragments/source/docs in order, re-validates the hypothesis, and maintains `tickets/12345/analysis.md`.
6. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - publish a KB article.
   - `/feature-request` - file a PM-facing request.

## Recommended model and effort

| Task | Model | Effort / thinking | Context |
|---|---|---|---|
| Working on project files (AGENTS.md, fragments, skills) | Sonnet | high | standard, 1M if needed |
| Ticket investigation | Opus | >= high | 1M |

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

## Skills / slash commands

Skills under `.agents/skills/` carry `user-invocable: true` and double as Claude Code slash commands via the symlinks in `.claude/commands/`.

### Investigation

- **`/investigate <ticket-ID>`** - run the full investigation pipeline: file inventory, scope inference, version alignment, tiered search (fragments → source → docs), re-validation, conclusion framing, and analysis log maintenance. Also accepts a free-text problem description instead of a ticket ID.

### Repo management

- **`/bootstrap`** - clone missing upstream repos and create working directories. Idempotent.

- **`/git-pull [<repo>]`** - `git pull --ff-only`.
  - No argument: pulls all repos.
  - `<repo>`: pulls one repo.

- **`/git-switch <repo> [<ref>]`** - switch to a tag, branch, or commit.
  - No ref: returns to the default branch.
  - `<ref>`: switches to a tag (e.g. `v10.5.1`), branch, or commit.

### Output

- **`/draft-reply [description]`** - draft a customer reply (email, Zendesk, hub thread) from the current troubleshooting context.
- **`/kb-article [description]`** - generate a KB article (Markdown + HTML).
- **`/feature-request [title]`** - generate a structured PM-facing feature-request post.
- **`/clipboard [content]`** - copy to OS clipboard (`pbcopy` / `Set-Clipboard` / `wl-copy`). No arg = most recent artifact.

## TODO

- [ ] Backfill `fragments/<repo>.md` incrementally from commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe), keeping only the irreducible TSE wisdom (misleading log signatures, license-tier traps, customer-misunderstanding decoders, version-specific gotchas).
- [ ] Tune `.claude/settings.local.json` so it auto-allows the commands needed for normal workflows here but denies questionable ones - especially relevant in auto mode.
- [ ] Evaluate persistent codebase memory/graph tooling for faster source lookups: `https://github.com/DeusData/codebase-memory-mcp`, `https://github.com/CodeGraphContext/CodeGraphContext`, or `ast-grep` as alternatives.
- [ ] Update `/feature-request` slash command from the upstream `techsupport-agent` version.
