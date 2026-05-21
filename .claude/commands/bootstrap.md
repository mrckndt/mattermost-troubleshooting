---
description: Clone any missing Mattermost repos into upstream/. Idempotent.
---

Apply the Shell conventions from `CLAUDE.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Clone every repo listed below under `upstream/<name>/`. For each URL:

1. Derive `<name>` from the last path segment of the URL.
2. If `upstream/<name>/` already exists, skip and report `already present`.
3. Otherwise run `git clone <url> upstream/<name>` and report `cloned` or the git error.

Continue on errors; collect failures and surface them at the end.

Ensure important working directories exist: `mkdir -p upstream tickets graphs graphs/_bundles`.

Repos to bootstrap (alphabetical):

- `https://github.com/mattermost/calls-offloader`
- `https://github.com/mattermost/calls-recorder`
- `https://github.com/mattermost/calls-transcriber`
- `https://github.com/mattermost/desktop`
- `https://github.com/mattermost/docker`
- `https://github.com/mattermost/docs`
- `https://github.com/mattermost/mattermost`
- `https://github.com/mattermost/mattermost-developer-documentation`
- `https://github.com/mattermost/mattermost-helm`
- `https://github.com/mattermost/mattermost-mobile`
- `https://github.com/mattermost/mattermost-operator`
- `https://github.com/mattermost/mattermost-plugin-agents`
- `https://github.com/mattermost/mattermost-plugin-boards`
- `https://github.com/mattermost/mattermost-plugin-calls`
- `https://github.com/mattermost/mattermost-plugin-channel-automation`
- `https://github.com/mattermost/mattermost-plugin-github`
- `https://github.com/mattermost/mattermost-plugin-gitlab`
- `https://github.com/mattermost/mattermost-plugin-google-calendar`
- `https://github.com/mattermost/mattermost-plugin-jira`
- `https://github.com/mattermost/mattermost-plugin-mscalendar`
- `https://github.com/mattermost/mattermost-plugin-msteams`
- `https://github.com/mattermost/mattermost-plugin-msteams-meetings`
- `https://github.com/mattermost/mattermost-plugin-playbooks`
- `https://github.com/mattermost/mattermost-plugin-zoom`
- `https://github.com/mattermost/migration-assist`
- `https://github.com/mattermost/rtcd`

Report a Markdown table: `Repo | Result`, where `Result` is `already present`, `cloned`, or the git error.

Notes:
- Run each `git clone` as its own Bash tool call; do not chain or append `2>&1`. Parallelize across repos in a single message.
- This command does NOT pull or switch. Use `/git-pull` (pulls + cascades graph updates), `/git-switch <repo> <ref>` (pin to tag/branch), or `/graphify-update` (refresh graphs without touching git).
- This file is the canonical repo list. `CLAUDE.md` and `README.md` reference it rather than duplicating URLs.
- The graph build phase is independent of cloning; run `/graphify-build <selector>` to build graphs.
