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
    ├── commands/          # /bootstrap, /git-pull, /git-switch
    └── settings.local.json
```

## Slash commands

- `/bootstrap` - clone any missing upstream repos.
- `/git-pull [<repo>]` - `git pull --ff-only` on the current branch of one repo or all.
- `/git-switch <repo> [<ref>]` - check out a tag or branch (default: the repo's default branch).

## Working a ticket

1. Create a folder under `tickets/` - named after the ticket ID or any other identifier: `tickets/12345/`, `tickets/customer-name/`, etc.
2. Drop relevant files there (logs, config dumps, support packets, screenshots, etc.).
3. Open Claude Code from the **repo root**:
   ```
   cd /path/to/mattermost-troubleshooting
   claude
   ```
4. Reference ticket files in your prompt (e.g. `@tickets/12345/mattermost.log`) or just describe the issue - the agent looks under `./tickets/` by default.

## First-time setup

Run `/bootstrap` to clone the upstream repos, then `/git-pull` to bring them current.
