# mattermost-troubleshooting

Workspace for the Claude-Code-driven Mattermost Technical Support Engineer agent. Local clones of upstream Mattermost repos plus curated per-repo CLAUDE.md fragments.

## Layout

```
.
├── CLAUDE.md              # Top-level agent instructions
├── claude-md/             # Per-upstream-repo CLAUDE.md fragments (imported by CLAUDE.md)
├── upstream/              # Local clones, one directory per upstream repo
├── tickets/               # One subfolder per ticket or investigation (e.g. tickets/12345/, tickets/customer-name/)
└── .claude/
    ├── commands/          # /bootstrap, /git-pull, /git-switch, /draft-reply, /kb-article, /feature-request
    └── settings.local.json
```

## Slash commands

**Repo management**
- `/bootstrap` - clone any missing upstream repos and create `tickets/` if absent.
- `/git-pull [<repo>]` - `git pull --ff-only` on the current branch of one repo or all.
- `/git-switch <repo> [<ref>]` - check out a tag or branch (default: the repo's default branch).

> Note: these three commands begin by `cd`-ing the shell to the project root if it isn't already there. A previous skill or tool may have left the shell in a subdirectory; relative paths like `upstream/<repo>` would silently misroute. The check uses the `pwd` value plus the presence of the tracked top-level entries (`CLAUDE.md`, `README.md`, `.gitignore`, `.claude/`, `claude-md/`, `upstream/`).

**Output**
- `/draft-reply [description]` - draft a customer reply from the current troubleshooting context. Optional arg: problem/solution hint.
- `/kb-article [description]` - generate a KB article (Markdown + HTML) from the current troubleshooting context. Optional arg: problem/solution hint.
- `/feature-request [title]` - generate a structured feature-request post (for PMs) from the current troubleshooting context. Optional arg: feature title or description.

## First-time setup

```
git clone git@github.com:mrckndt/mattermost-troubleshooting.git
cd mattermost-troubleshooting
claude
```

Then inside Claude:
- `/bootstrap` - clone all upstream repos under `upstream/` and create `tickets/`.

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
5. Reference ticket files in your prompt (e.g. `@tickets/12345/mattermost.log`) or just describe the issue - the agent looks under `./tickets/` by default.
6. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - publish a KB article.
   - `/feature-request` - file a PM-facing request.
