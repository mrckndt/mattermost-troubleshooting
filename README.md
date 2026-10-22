# mattermost-troubleshooting

AI agent workspace for Mattermost Technical Support Engineers. Given a ticket, the investigation pipeline pins upstream source to the customer's exact version, searches code, docs, and curated knowledge fragments exhaustively, and produces a root-cause finding with evidence. Output skills generate customer replies, KB articles, and PDE intake posts from the same session.

The workspace currently runs on Claude Code only. Support for other agent frameworks is a long-term goal, which is why instructions live in `AGENTS.md` and skills in `.agents/skills/`.

## Quickstart

```
git clone git@github.com:mrckndt/mattermost-troubleshooting.git
cd mattermost-troubleshooting
claude
```

Then inside Claude:
```
/bootstrap
/hub-harvest 12345
/investigate 12345
```

`/bootstrap` clones all upstream repos under `upstream/` and creates the `tickets/` directory. Idempotent - safe to re-run.
`/hub-harvest` and `/investigate` are covered in "Working a ticket".

> `/bootstrap` and `/git-pull` are mechanical shell operations - **Claude Haiku 5.5** or **Claude Sonnet 5.5** at default effort is enough.

## Recommended setup

Not required to get started, but strongly recommended: each item below widens what the pipeline can search or do.
`gh` and codebase memory are the least load-bearing and the safest to skip: no core workflow depends on them
(`/investigate` runs without either).

### CLI tools (`fd`, `rg`, `gh`)

Skill instructions show `rg`/`fd` first, with `grep`/`find` as the no-install fallback. Both are faster and,
being Rust, memory-safe on untrusted ticket files; `AGENTS.md`'s Search tools bullet lists the flags that keep them equivalent.

`gh` (GitHub CLI) gives access to GitHub issues and PRs similar to the GitHub MCP connector, and covers for
it when the connector is unavailable, ahead of WebFetch/WebSearch. Authenticate once with `gh auth login`.

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

### MCP integrations

The investigation pipeline consults these MCP-backed sources when their tools are available:

- **Mattermost Hub** - the enterprise Claude connector (`mcp__claude_ai_Mattermost_Hub__*`). No local setup; available when your Claude account has the connector enabled.
- **GitHub issues/PRs** - `github.com/mattermost/*`, via the claude.ai GitHub MCP connector.
- **Internal Jira (engineering tickets)** - project `MM` only, via the claude.ai Atlassian MCP connector.
- **Gmail** - drafts and sends Sev1/Sev2 escalation-workflow emails (`/sev-email`), via the claude.ai Gmail connector.
- **Codebase memory** - a knowledge-graph index of `upstream/<repo>/` clones via [`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp), run locally. Lets `/investigate`
  attribute text matches to the functions that contain them and trace call chains (who calls what).

When a source's tools are not present, `/investigate` skips it with a noted reason and relies on local data (`fragments/`, `upstream/`) and the fallbacks listed below.

#### GitHub, Jira, and Gmail connector setup

These three all connect the same way, through the Anthropic connectors page:

1. Go to `https://claude.ai/customize/connectors`, add/connect the relevant connector, and authorize.
2. In Claude Code, run `/mcp` and select it.

Per-connector specifics:

- **GitHub** - registers as `claude.ai GitHub MCP`, tools under `mcp__claude_ai_GitHub_MCP__*`. This is the pipeline's GitHub source, alongside the `gh` CLI, which offers similar access and covers when the connector is unavailable; then WebFetch/WebSearch. If a query fails with an org SAML SSO error, disconnect and reconnect via `/mcp` and retry.
- **Jira (Atlassian connector)** - this is the pipeline's internal Jira source (project `MM` only); no public fallback if unavailable.
- **Gmail** - registers as `claude.ai Gmail`, tools under `mcp__claude_ai_Gmail__*`. This is `/sev-email`'s only send path; no fallback if unavailable - the skill says so and stops before drafting.

#### Codebase memory MCP setup

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

`--skip-config` installs the binary only; without it the installer registers a conflicting MCP name and global
hooks/skills that duplicate this repo's. Undo with `codebase-memory-mcp uninstall`.

Register with Claude Code - the name must be `codebase_memory_local` exactly (the pipeline looks for the `mcp__codebase_memory_local__*` prefix):
```
claude mcp add codebase_memory_local "$(command -v codebase-memory-mcp)"
```
Restart Claude Code so the session loads the tools; verify with `claude mcp list`.

Indexing happens automatically during `/investigate`. Data lives in `~/.cache/codebase-memory-mcp/`; delete that directory to reset.

## Working a ticket

Run all commands from the repo root (`mattermost-troubleshooting/`).

1. Open Claude Code:
   ```
   claude
   ```

   > **Claude Opus 5.5** or **Claude Sonnet 5.5** at default effort (medium); raise it to high or xhigh for hard cases.
   > Auto mode is recommended from `/hub-harvest` on.

2. Fetch the ticket thread: `/hub-harvest 12345`. This creates `tickets/12345/` and writes the full Zendesk
   thread to `zendesk-thread.md`.

   You may also want to add ticket files the thread doesn't carry (logs, config dumps, support packets,
   screenshots) to the same folder before investigating:
   ```
   cp ~/Downloads/mattermost.log tickets/12345/
   cp ~/Downloads/support_packet.zip tickets/12345/
   ```

   If the ticket isn't mirrored to the Hub, create the folder yourself (`mkdir -p tickets/12345`) and drop the files there.
3. Run the investigation pipeline: `/investigate 12345`.

   This command reads every ticket file, pins `mattermost`, `enterprise`, and any in-scope plugin repos to the customer's exact version, then searches exhaustively before forming a hypothesis:
   - Searches source code at five angles (exact error strings, config keys, stack trace functions, feature flag and setting key names, symptom keywords) - all required, no skipping.
   - Searches important upgrade notes, all server changelogs, product docs, developer docs, Mattermost Hub, and GitHub issues per repo - all required.
   - Blocks the hypothesis until all search angles are exhausted and at least two alternatives have been actively disproved.
   - Returns a `function:file` root cause, a Hub/GitHub cross-reference if the issue is known, and writes `tickets/12345/analysis.md` once the investigation concludes, ready for handoffs or a later `/resume-investigation`.

   Add `--no-cbm` (e.g. `/investigate 12345 --no-cbm`) to run without the codebase-memory knowledge graph.
   Source search then uses `rg --no-ignore --hidden` (or `grep`)/`git` alone: coverage is unchanged, and what you give up is symbol
   attribution for text matches and call-chain tracing. Useful for config questions and known-issue
   lookups where speed matters more than structural evidence.
4. When you have a conclusion, generate the output (customer reply, KB article, RCA, PD&E intake, and more) with
   the skills listed under "Skills / slash commands > Output".

## Skills / slash commands

Skills under `.agents/skills/` double as Claude Code slash commands via the symlinks in `.claude/commands/`.

### Investigation

- **`/hub-harvest <ticket-ID|assignee-email|hub-thread-link> [time-range]`** - fetch a Zendesk ticket thread from the Mattermost Hub into `tickets/<zd#>/zendesk-thread.md`, ready for `/investigate`. Accepts a pasted Hub thread permalink directly. Given an assignee email instead, harvests every thread assigned to that TSE in the time window (default: last 30 days) and additionally writes an index at `tickets/hub-harvest/<emaillocalpart>-<date>.md`, grouped by status.
- **`/investigate <ticket-ID|ticket-URL|description>`** - the core skill. See the expanded description in "Working a ticket", step 3.

### Output

- **`/draft-reply [description]`** - draft a customer reply (email, Zendesk, hub thread) from the current troubleshooting context.
- **`/kb-article [ticket-ID|description]`** - generate a KB article (Markdown + HTML). Given a ticket ID (or one already active in the session), reads that ticket's `zendesk-thread.md`/`analysis.md` and saves to `tickets/<ID>/kb-article.md`+`.html`; otherwise saves to `kb-articles/<slug>-<date>.md`+`.html` at the project root.
- **`/kb-batch <assignee-email> [time-range]`** - bulk-draft KB articles for a TSE's assigned Zendesk tickets in a window: harvests threads via `/hub-harvest`, drafts one article per ticket with `/kb-article`, then walks you through proofreading one at a time. Tracks progress in `tickets/kb-batch/<emaillocalpart>-<date>.md`; resumable and re-runnable to pick up new/updated tickets.
- **`/product-request [title]`** - generate a structured PD&E intake post (feature request, bug report, or security issue). After printing, asks whether to send it as a Hub DM to the PDE Intake Agent (`@pde-intake`, requires the Mattermost Hub connector). `/pde-intake [title]` is a deprecated alias.
- **`/rca [ticket-ID]`** - generate a customer-facing Root Cause Analysis report from `tickets/<ID>/analysis.md` (and `eir.md` if present); saves to `tickets/<ID>/rca.md`.
- **`/eir [ticket-ID]`** - generate an internal Engineering Incident Report from `tickets/<ID>/analysis.md`, plus GitHub/Jira lookups; saves the full report to `tickets/<ID>/eir.md` and prints a compact channel-post summary.
- **`/retro [ticket-ID]`** - run a post-resolution retrospective (investigation retrospective, follow-ups, KB article, docs/KB review); saves to `tickets/<ID>/retro.md`. Requires a confirmed root cause in `analysis.md`.
- **`/upgrade-advisor [ticket-ID|version]`** - generate an upgrade recommendation report comparing a ticket's support-packet/config version (or an explicit version) to the latest patch: security fixes, urgent vs quality-of-life bugs, plugin updates; saves to `tickets/<ID>/upgrade-advisor.md` when run from a ticket. Does not require `analysis.md`.
- **`/sev-email <ticket-ID> [stage]`** - draft (and, after review, send via Gmail) a Sev1/Sev2 escalation-workflow email: Initial Notification, Workaround Guidance, Resolution & De-escalation, or Postmortem Information. `/sev-escalation` is a deprecated alias. Tracks the Gmail thread in `tickets/<ID>/gmail-escalation-thread.md`.
- **`/escalation-helper <ticket-ID> [packet | postmortem]`** - show where a ticket stands in the escalation process (path, Technical Escalation Playbook checklist, #radar emails, optionally the run channel's posts via Hub): done and missing, then runs the chosen item's skill (`/sev-email`, `/kb-article`, `/investigate`, `/draft-reply`) on confirmation. Engineer answers persist in `tickets/<ID>/escalation-status.md` across runs. `packet` exports the Escalation Packet (Support to Engineering Escalation Template) from `analysis.md` to `tickets/<ID>/escalation-packet.md` and, on confirmation, posts it to the run channel. `postmortem` drafts `tickets/<ID>/postmortem.md` from the playbook's retrospective template.
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

### Ticket management

- **`/resume-investigation <ticket-ID>`** - reconstruct context from `analysis.md` if present, then ask before re-running `/investigate`; runs `/investigate` unprompted only if no prior analysis exists.
- **`/search-tickets <keyword>`** - search across all past ticket files and analysis logs; groups results by ticket ID with context snippets.
- **`/resolve-ticket-id [--allow-new] <reference>`** - normalize a ticket reference (bare number, `zd-`/`ZD-` prefix, Zendesk URL) to a numeric ID.
  Verifies `tickets/<id>/` exists unless `--allow-new`. Returns the ID or `no-match`.

## Layout

```
.
├── AGENTS.md                # Top-level agent instructions
├── CLAUDE.md                # Claude Code entry point: @-imports AGENTS.md
├── fragments/               # Per-upstream-repo knowledge fragments
├── upstream/                # Local clones, one directory per upstream repo
├── tickets/                 # One subfolder per ticket or investigation (e.g. tickets/12345/); tickets/hub-harvest/ holds /hub-harvest assignee-mode indexes
├── kb-articles/             # Standalone KB articles from /kb-article when no ticket is in play
├── .agents/
│   ├── config/
│   │   └── repos.json       # Upstream repo list; cbm_excluded flags repos excluded from codebase-memory indexing
│   └── skills/              # Canonical skill definitions (SKILL.md per skill)
└── .claude/
    ├── commands/            # Symlinks to .agents/skills/*/SKILL.md - required for Claude Code slash command discovery
    └── settings.local.json  # Claude Code-specific: allowed tools and project-level settings
```
