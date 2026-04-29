# mattermost-troubleshooting

Workspace for the Claude-Code-driven Mattermost Technical Support Engineer agent. Local clones of upstream Mattermost repos plus curated per-repo CLAUDE.md fragments.

## Layout

```
.
├── CLAUDE.md              # Top-level agent instructions
├── claude-md/             # Per-upstream-repo CLAUDE.md fragments (imported by CLAUDE.md)
├── upstream/              # Local clones, one directory per upstream repo
└── .claude/
    ├── commands/          # /bootstrap, /sync, /switch
    └── settings.local.json
```

## Slash commands

- `/bootstrap` - clone any missing upstream repos.
- `/sync [<repo>]` - `git pull --ff-only` on the current branch of one repo or all.
- `/switch <repo> [<ref>]` - check out a tag or branch (default: the repo's default branch).

## First-time setup

Run `/bootstrap` to clone the upstream repos, then `/sync` to bring them current.
