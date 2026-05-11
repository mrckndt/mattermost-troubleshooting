# mattermost-troubleshooting

Workspace for the Claude-Code-driven Mattermost Technical Support Engineer agent. Local clones of upstream Mattermost repos, curated per-repo CLAUDE.md fragments, and on-disk knowledge graphs.

> Looking for the previous setup (full `claude-md/<repo>.md` content, no `graphs/`, no `/graphify-*` commands)? Check out commit [`5936874`](https://github.com/mrckndt/mattermost-troubleshooting/commit/5936874e561203f4336e509e9c89f6a539f69ebe) - the last state before the graphify integration. The `claude-md/` files there contain the prior TSE notes that are now being re-curated alongside the knowledge graphs.

## Layout

```
.
├── CLAUDE.md              # Top-level agent instructions
├── claude-md/             # Per-upstream-repo CLAUDE.md fragments (imported by CLAUDE.md)
├── upstream/              # Local clones, one directory per upstream repo
├── graphs/                # Knowledge-graph outputs (gitignored except graphs/config.json)
│   ├── config.json        # repo scopes + bundle definitions
│   ├── <repo>/            # per-repo graph
│   ├── _bundles/<name>/   # named cross-repo bundle (e.g. calls)
│   └── _all/              # mega-graph across everything that's been built
├── tickets/               # One subfolder per ticket or investigation (e.g. tickets/12345/, tickets/customer-name/)
└── .claude/
    ├── commands/          # /bootstrap, /git-pull, /git-switch, /graphify-scope, /graphify-update, /graphify-bundle, /draft-reply, /kb-article, /feature-request
    └── settings.local.json
```

## Slash commands

**Repo management**
- `/bootstrap` - clone any missing upstream repos and create `tickets/` if absent. With `--build <calls|all|<repo>>` it also runs the initial graphify build (otherwise it prompts).
- `/git-pull [<repo>]` - `git pull --ff-only` on the current branch of one repo or all. Cascades a graphify `--update` for any repo whose HEAD moved, then re-merges affected bundles and `_all`.
- `/git-switch <repo> [<ref>]` - check out a tag or branch (default: the repo's default branch). Rebuilds or `--update`s the repo's graph based on the change ratio, then re-merges affected bundles and `_all`.

**Knowledge graph**
- `/graphify-scope` - show available scopes (per-repo, bundle, `_all`) and the current pin.
- `/graphify-scope <scope>` - pin a scope so all subsequent graphify queries hit it. `<scope>` is a repo name, a bundle name, or `_all`.
- `/graphify-scope clear` - remove the pin; auto-select resumes (see `CLAUDE.md` for the heuristic).
- `/graphify-update` - incrementally refresh all built graphs (per-repo `--update`, then re-merge bundles and `_all`).
- `/graphify-update <repo>` - update one repo and cascade to its bundles and `_all`.
- `/graphify-update <bundle-name>` - re-merge + re-cluster one bundle from existing per-repo graphs (e.g. `/graphify-update calls`).
- `/graphify-update _all` - re-merge + re-cluster `_all` from all existing per-repo graphs.
- `/graphify-bundle` - list defined bundles (name, repos, keywords, built status).
- `/graphify-bundle <name>` - show one bundle's details.
- `/graphify-bundle add <name> [<repos>] [<keywords>]` - create a bundle. `<repos>` and `<keywords>` are optional comma-separated lists.
- `/graphify-bundle remove <name>` - delete a bundle from config and remove its built graph (if any).

> Note: `/bootstrap`, `/git-pull`, `/git-switch`, `/graphify-scope`, `/graphify-update`, and `/graphify-bundle` all begin by `cd`-ing the shell to the project root if it isn't already there. A previous skill or tool may have left the shell in a subdirectory; relative paths like `upstream/<repo>` or `graphs/<scope>` would silently misroute. The check uses the `pwd` value plus the presence of the tracked top-level entries (`CLAUDE.md`, `README.md`, `.gitignore`, `.claude/`, `claude-md/`, `upstream/`, `graphs/`).

**Output**
- `/draft-reply [description]` - draft a customer reply from the current troubleshooting context. Optional arg: problem/solution hint.
- `/kb-article [description]` - generate a KB article (Markdown + HTML) from the current troubleshooting context. Optional arg: problem/solution hint.
- `/feature-request [title]` - generate a structured feature-request post (for PMs) from the current troubleshooting context. Optional arg: feature title or description.

## First-time setup

### Install graphify

Graphify is a separate Python CLI used to build the knowledge graphs under `graphs/`. Install it before running `/bootstrap --build` so the initial graph build can happen. (`/bootstrap` without `--build` still works without graphify installed; you can install it later and run `/bootstrap --build calls`.)

**macOS (pipx)** - recommended:

```
brew install pipx
pipx ensurepath
pipx install graphifyy
```

**macOS (Homebrew + venv)** - if you prefer Homebrew's Python directly:

```
brew install python
python3 -m venv ~/.venvs/graphify
~/.venvs/graphify/bin/pip install graphifyy
# add ~/.venvs/graphify/bin to PATH, or symlink:
ln -s ~/.venvs/graphify/bin/graphify /usr/local/bin/graphify
```

**Windows**:

```
# Install Python 3.10+ from python.org first, then:
python -m pip install --user pipx
python -m pipx ensurepath
pipx install graphifyy
```

Verify: `graphify --help` should print usage.

### Graphify build cost and model choice

Graphify's build pipeline has two extraction phases with very different costs:

- **AST extraction** (code files): deterministic parsing, no LLM calls, cached after the first run. Incremental updates (`/graphify-update`) that touch only code are essentially free.
- **Semantic extraction** (doc/paper/image files): one Claude or Gemini subagent call per ~22-file chunk. This is where cost accumulates.

**Use Gemini for initial builds** - it is significantly cheaper than Claude for the high-volume semantic extraction that happens on a first build. Install the extra dependency and set the key before running `/bootstrap --build`:

```
pipx inject graphifyy 'graphifyy[gemini]'
export GEMINI_API_KEY=<your-key>   # or GOOGLE_API_KEY
```

The default Gemini model is `gemini-3-flash-preview` (fast, cheap). Override with `GRAPHIFY_GEMINI_MODEL` if needed.

**If you use Anthropic instead**, choose the model and effort level deliberately:

| Use case | Recommended | Why |
|---|---|---|
| Initial build or full rebuild | Sonnet 4.6 at low effort, or Haiku 4.5 at default | Semantic subagents are simple extraction tasks; Opus is overkill and 5-10x more expensive |
| Incremental update (code only) | Any model | No LLM calls - AST only |
| TSE troubleshooting sessions | Sonnet 4.6 (default) | Good balance of reasoning and cost |

**Do not use Opus for graphify builds.** Semantic extraction dispatches tens to hundreds of subagents on a large repo. At Opus pricing this is expensive without any quality gain over Sonnet or Haiku - the task is structured data extraction, not complex reasoning.

### Clone and start

```
git clone git@github.com:mrckndt/mattermost-troubleshooting.git
cd mattermost-troubleshooting
claude
```

Then inside Claude:
- `/bootstrap` - clone all upstream repos under `upstream/` and create `tickets/`. By default it prompts whether to build any graphify graphs; pick `calls` for the initial Calls bundle (six repos), `all` for everything, or `skip` to defer.

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
   - This also rebuilds or updates the repo's knowledge graph and re-merges affected bundles.
5. Optionally pin the graph scope for the session so the agent always queries the right graph:
   - `/graphify-scope calls` for a Calls ticket.
   - `/graphify-scope <repo>` for a single-repo ticket (e.g. `/graphify-scope mattermost-plugin-github`).
   - `/graphify-scope _all` for cross-cutting research.
   - `/graphify-scope clear` when you're done.
6. Reference ticket files in your prompt (e.g. `@tickets/12345/mattermost.log`) or just describe the issue - the agent looks under `./tickets/` by default.
7. When you have a conclusion, generate the customer-facing output:
   - `/draft-reply` - reply to the customer.
   - `/kb-article` - publish a KB article.
   - `/feature-request` - file a PM-facing request.
