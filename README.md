# mattermost-troubleshooting

Workspace for the Claude-Code-driven Mattermost Technical Support Engineer agent. Local clones of upstream Mattermost repos and curated per-repo CLAUDE.md fragments.

## Layout

```
.
├── CLAUDE.md                # Top-level agent instructions
├── claude-md/               # Per-upstream-repo CLAUDE.md fragments (imported by CLAUDE.md)
├── upstream/                # Local clones, one directory per upstream repo
├── tickets/                 # One subfolder per ticket or investigation (e.g. tickets/12345/, tickets/customer-name/)
└── .claude/
    ├── commands/            # /bootstrap, /git-pull, /git-switch, /draft-reply, /kb-article, /feature-request, /clipboard
    └── settings.local.json  # Project-level Claude Code settings file, mainly containing allowed tools
```

## Setup

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
- `/bootstrap` - clone all upstream repos under `upstream/` and create the working directories.

### Working a ticket

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
4. Pin the repo to the customer's version if needed: `/git-switch mattermost v10.5.1`.
5. Describe the issue or reference ticket files directly (`@tickets/12345/mattermost.log`). The agent checks `./tickets/` by default.
6. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - publish a KB article.
   - `/feature-request` - file a PM-facing request.

## Slash commands

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

## TSE notes backfill

The `claude-md/<repo>.md` files on this branch are header-only stubs for most repos. The prior TSE notes live at commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe) and are being re-curated incrementally, trimmed to what upstream docs and source cannot reproduce: misleading log signatures, license-tier traps, customer-misunderstanding decoders, version-specific gotchas.

## TODO

- [ ] Backfill `claude-md/<repo>.md` incrementally from commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe), keeping only the irreducible TSE wisdom.
- [ ] Figure out the proper way to include private repos like `enterprise` (clone-time auth, agent visibility, what to commit vs. keep local).
- [ ] Tune `.claude/settings.local.json` so it auto-allows the commands needed for normal workflows here but denies questionable ones - especially relevant in auto mode.
- [ ] Implement an end-to-end ticket-troubleshooting flow the agent runs on request (e.g. a `/triage <ticket-id>` skill): extract the support packet, read the logs / config, query for likely causes, save running findings to `tickets/<id>/analysis.md`, and stage the customer artifact via `/draft-reply` or `/kb-article` when the user is ready.
