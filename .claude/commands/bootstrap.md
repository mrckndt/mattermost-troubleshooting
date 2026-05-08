---
description: Clone any missing Mattermost repos into upstream/. Idempotent - skips repos already present.
---

First verify the shell is at the project root - a prior skill/tool may have left it in a subdirectory, silently misrouting relative paths like `upstream/<name>`. Run `pwd && ls -1 CLAUDE.md README.md .gitignore .claude claude-md upstream`. If `pwd` doesn't end in `/mattermost-troubleshooting` or any entry is missing, `cd` (absolute path) to the root before continuing.

Ensure every repo listed below is cloned under `upstream/<name>/` in the current working directory. For each URL:

1. Derive `<name>` from the last path segment of the URL (e.g. `https://github.com/mattermost/mattermost` -> `mattermost`).
2. If `upstream/<name>/` already exists, skip and report `already present`.
3. Otherwise run `git clone <url> upstream/<name>` and report `cloned` or the error message git printed.

Continue on errors; collect failures and surface them at the end.

Also ensure a `tickets/` directory exists at the working-directory root. If it's missing, create it: `mkdir tickets` (works on macOS / Linux and on Windows cmd / PowerShell). If it already exists, leave it alone - the engineer may have organised it differently and any internal structure is theirs to keep.

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

Report a Markdown table with one row per repo and the columns: `Repo | Result`.
- `Result`: `already present`, `cloned`, or the error message git printed.

Notes:
- Run each `git clone` as its own Bash tool call. Do not chain with `&&`, `;`, or pipes; do not append `2>&1`. Parallelize across repos in a single message.
- This command does NOT pull or switch. After bootstrap, run `/git-pull` to bring all repos to their latest tracked state, or `/git-switch <repo> <ref>` to pin one to a specific tag/branch.
- This file is the canonical list of expected repos. `CLAUDE.md` and `README.md` reference it rather than duplicating the URLs.
