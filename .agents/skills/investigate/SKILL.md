---
name: investigate
description: Run the full investigation pipeline for a ticket or problem description. Enforces phase order (fragments + upgrade notes → source → docs → re-validation → conclusion), scope inference, version alignment, and analysis log maintenance.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

**Complete each phase in order. Do not skip ahead, form hypotheses, or run source searches until the phase explicitly permits it.**

- No hypotheses until Phase 1's inventory output (severity table, distinct-msg sweep, error-families list) is in the conversation.
- Phases 4-6 must all complete before forming hypotheses or drawing conclusions. No early stopping.
- After any Phase 5 source hit, re-check the error-families list for unexplained entries before narrowing.

## Phase 0 - Setup and argument resolution

Determine mode:
- If `$ARGUMENTS` matches a directory under `tickets/` (check with `ls "$PROJECT_ROOT/tickets/$ARGUMENTS"` or similar): **ticket mode** - set `<ID>=$ARGUMENTS`.
- Otherwise: **description mode** - the argument is a problem description. Skip Phase 1 and the Version-alignment file-based detection in Phase 3; proceed using the description as the only input.

If no argument is provided, list `tickets/` subdirectories and ask which ticket to investigate before proceeding.

Complete this phase before proceeding.

## Phase 1 - Ticket file inventory

Before listing files, unarchive any archives in `tickets/<ID>/` in place:

```
for f in tickets/<ID>/*.zip; do unzip -n "$f" -d "tickets/<ID>/$(basename "$f" .zip)"; done
for f in tickets/<ID>/*.tar.gz tickets/<ID>/*.tgz; do tar -xzf "$f" -C "tickets/<ID>/"; done
```

Skip silently if no archives are present. Do not delete the original archives.

Then list every file in `tickets/<ID>/` with sizes, then read each one before forming any hypothesis:

```
ls -lh tickets/<ID>/
```

- Files under 100 KB: read in full.
- Files 100 KB to 1 MB: read head (first 200 lines) + tail (last 200 lines).
- Files over 1 MB: read head (first 100 lines) + tail (last 100 lines) + `rg`/`grep` for `error`, `warn`, `fatal`, `crash`, `panic`, `exception`.

For extracting specific fields or sections from any file (including JSON and YAML config files), use `rg` or `grep`.


Do not begin scope inference until all files have been inventoried this way.

### Inventory output (required)

Once all ticket files are read, emit a single fenced block containing:

0. `Files: N listed, N read` - counts must match; if they differ, the gate is not satisfied.

1. A bulleted list with one item per file. Lead with path and size; follow with a one-line
   characterization. **Bold any anomaly, misconfiguration, or error count that warrants attention**:

   - **`<path>`** (`<size>`) - `<characterization with **key findings bolded**>`

2. A freeform **error-families list**: distinct error-level messages across all files, deduped.

This block is the gate. Phase 2 cannot start, no `fragments/` fragment may be opened, and no hypothesis may be stated
until this block is present in the conversation. Partial inline greps do not satisfy the gate; it must appear as one contiguous artifact.
If you have already read source or stated a hypothesis without this block, stop and emit it now.

Complete this phase before proceeding.

## Phase 2 - Scope inference

After the file inventory, identify in-scope repos and fragments by judgment first (anything mentioned or implied by symptoms); the table below is a backstop for keywords and multi-repo families. Don't anchor to it - unlisted repos must still surface.

| Signal in ticket / logs | Repos / fragments |
|---|---|
| desktop, Electron, macOS, Windows, Linux, server tab, deep link, GPO, MDM, Group Policy | `desktop` |
| Docker, docker-compose | `docker` |
| mobile, push notification, iOS, Android, React Native, push proxy, TestFlight, certificate pinning, WatermelonDB, MPNS | `mattermost-mobile` |
| Helm, operator, ingress, MinIO, Kubernetes, K8s, EKS, CRD, Cluster | `mattermost-operator`, `mattermost-helm` |
| mattermost-ai, AI, Agents, Copilot, LLM, OpenAI, Anthropic, AWS Bedrock, Google Gemini, Ollama, MCP, pgvector, semantic search, RAG | `mattermost-plugin-agents` |
| Boards, Focalboard, kanban, tasks | `mattermost-plugin-boards` |
| calls, meeting, voice calling, screen sharing, WebRTC, ICE, STUN, TURN, SFU, NAT, TURN credentials, IPv6, packet loss, RTCD, recording, transcription, transcript, job service, recording job, transcribing job, ffmpeg, Chromium, Xvfb | `mattermost-plugin-calls`, `rtcd`, `calls-offloader`, `calls-recorder`, `calls-transcriber` |
| channel automations, flow, workflow, trigger, schedule | `mattermost-plugin-channel-automation` |
| Confluence, wiki, pages | `mattermost-plugin-confluence` |
| GitHub, notifications, repo subscription | `mattermost-plugin-github` |
| GitLab, notifications | `mattermost-plugin-gitlab` |
| Google Calendar, GCal, event reminder | `mattermost-plugin-google-calendar` |
| Jira, channel subscription, webhook, notifications | `mattermost-plugin-jira` |
| MS Calendar, Outlook, event reminder | `mattermost-plugin-mscalendar` |
| MS Teams, Teams sync  | `mattermost-plugin-msteams` |
| Teams, meeting, video calls, screen sharing | `mattermost-plugin-msteams-meetings` |
| Playbooks, incident, runs, retrospective, workflow | `mattermost-plugin-playbooks` |
| Zoom, meeting, video calls, screen sharing | `mattermost-plugin-zoom` |
| migration, MySQL to PostgreSQL, pgLoader, tsvector | `migration-assist` |
| Grafana, Prometheus, metrics, dashboard, performance monitoring | `mattermost-performance-assets` |

Complete this phase before proceeding.

## Phase 3 - Version alignment

Before Tier 2 source reads, verify each in-scope repo is on the customer's version.

When reading `mattermost.log`, always use the bottom-most matching entry; the log is append-only and upgrades and node restarts produce multiple identical-looking startup lines.

**Detect server version** (check in order; stop at first hit):
1. `tickets/<ID>/diagnostics.yaml` - `server.version` field
2. `tickets/<ID>/metadata.yml` - `server_version` field
3. `tickets/<ID>/mattermost.log` - line matching `"Current version is X.Y.Z"`
4. `tickets/<ID>/analysis.md` - `## Deployment` section
5. Conversation context or other ticket files

**Detect plugin versions** (when plugins are in scope) - check both sources:
1. `tickets/<ID>/plugins.json` - `version` field per plugin entry
2. `tickets/<ID>/mattermost.log` - bottom-most `"Installing extracted plugin"` line per `plugin_id`. Earlier installs were superseded by upgrades or rollbacks.
   Example: `rg "Installing extracted plugin" mattermost.log | rg <plugin_id> | tail -1`

**Align repos:**

`mattermost` and `enterprise` are tightly coupled and must always be on the same ref. Switch both together; never leave them on different versions.

1. For each in-scope repo, check current ref:
   ```
   git -C "$PROJECT_ROOT/upstream/<repo>" describe --tags --exact-match 2>/dev/null || \
     git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD
   ```
2. If the ref does not match the customer's version, run `/git-switch <repo> <version>`; it resolves `vX.Y.Z` tags, `X.Y`/`X.Y.Z` queries, and branch names.
3. Run `/git-pull` if on a branch; skip if on a tag (detached HEAD - tags are immutable).
4. After the investigation completes, state which version(s) the analysis was run against (mirroring the unknown-version footer).

**Unknown version:** run `/git-switch <repo> "latest esr"` for `mattermost` and `enterprise`; do not ask the engineer.

- After the investigation completes, state: "Version unknown; analysis run against `<esr-tag>` (current ESR). Re-run `/git-switch mattermost <version>` if customer version is known."
- Apply the same note for any plugin repos in scope.

Complete this phase before proceeding.

## Phase 4 - Fragment and Upgrade Notes Search

For each in-scope repo, check whether `fragments/<repo>.md` exists and Read it.
`mattermost` and `enterprise` always pair: if either is in scope, read both fragments.

Then search both files for the customer's version range - both are required, not alternatives:

1. Important upgrade notes:
```
grep -n "<keywords>" "$PROJECT_ROOT/upstream/docs/source/administration-guide/upgrade/important-upgrade-notes.rst"
```
2. v11 changelog:
```
grep -n "<keywords>" "$PROJECT_ROOT/upstream/docs/source/product-overview/mattermost-v11-changelog.md"
```

Search by server version, affected component, and any config keys or error strings from the inventory. If a version is known, also read the surrounding lines for each hit to capture the full note.

Complete this phase before proceeding.

## Phase 5 - Source Code Search

**Step 0: Ensure codebase-memory index.**
- For each in-scope repo that exists under `upstream/` (note any absent, e.g. `enterprise` if not cloned), run `/cbm-index-repository <repo>` inline.
- If it reports `codebase-memory MCP not present`: state `codebase-memory search skipped: MCP not present` once and run the grep-only form of every Step 2 angle.
- Do not call any other `/cbm-*` skill for the rest of this phase or Phase 7 when absent.
- Otherwise codebase-memory is available; use each repo's `Project` column value as `project` for every codebase-memory query below and in Phase 7.

**Step 1: AppError → i18n key lookup.**
- Applies only to Mattermost server logs; skip if none present.
- Identify server logs by filename (`mattermost.log`, `*mattermost*.log`, `*mattermost*.txt`) or by content (lines matching `level=(error|warn|info|debug).*msg=`).
- `<Message>` in `<Where>: <Message>` is almost always a translation key value - grepping it returns the precise call-site key.

1. Identify server language from the server log; check `ls upstream/mattermost/server/i18n/` for `<lang>.json`.
2. For any `level=error` line where `msg` is the localized "internal error" string, or any AppError-shaped string `<Where>: <Message>`, extract `<Message>` **exactly** - full punctuation, no paraphrasing, no truncation.
3. `grep -F "<message>" upstream/mattermost/server/i18n/<lang>.json` to get the key; `rg`/`grep` source for the call site.

**Step 2: Source search.** Always run against `upstream/mattermost/`, `upstream/enterprise/` (if cloned; may be absent if GitHub SSH key not configured), and all other inferred repos.
All five angles below are required, run once per in-scope repo; note `no matches` explicitly if a search returns nothing.

Where Step 0 found codebase-memory available, lead each angle with the named skill below, then confirm/cover gaps with `rg`/`grep`/`fd`/Read/Find. Where absent, the grep form is the whole angle.

1. Exact error strings from the Phase 1 error-families list: `/cbm-search-code <repo> "<string>"` for ranked leads.
   - **Then `rg --no-ignore --hidden`/`grep -F` as the authoritative exhaustive pass** (search_code caps at 10 results, no offset; bypassing default ignore-file filtering covers excluded dirs, i18n JSON, non-code files).
2. Config keys found in `sanitized_config.json` or `diagnostics.yaml`: `/cbm-search-graph <repo> <key>` to locate the setting struct/field, then `rg --no-ignore --hidden`/`grep`.
3. Function/method names from stack traces: `/cbm-trace-path <repo> <fn>` for callers/callees and `/cbm-get-code-snippet <repo> <fn>` for source, then `rg --no-ignore --hidden`/`grep`.
4. Feature flag or setting key names: `/cbm-search-graph <repo> <key>`, then `rg --no-ignore --hidden`/`grep`.
5. Symptom keyword (free-form, drawn from the reported symptom): `/cbm-search-graph <repo> <keyword>` (semantic), then `rg --no-ignore --hidden`/`grep`.
   - Broad keywords can return large, loosely-ranked result sets - treat the rg/grep exhaustive pass as the real filter here, not just confirmation of cbm's top hit.

Complete this phase before proceeding.

## Phase 6 - Docs and Issues Search

Search all five unconditionally - all are required:
1. `upstream/docs/source/` (product docs, customer-facing). Example: `rg -n "MaxOpenConns" upstream/docs/source/` / `grep -rn "MaxOpenConns" upstream/docs/source/`
2. `upstream/mattermost-developer-documentation/site/content/` (developer docs). Example: `rg -n "plugin manifest" upstream/mattermost-developer-documentation/site/content/` / `grep -rn "plugin manifest" upstream/mattermost-developer-documentation/site/content/`
3. Mattermost Hub: `mcp__claude_ai_Mattermost_Hub__search_posts` for symptom keywords and Phase 1 error strings.
   - Use focused 1-2 term queries (stricter AND-matches with more terms often return zero results). Leave `keyword_limit`/`semantic_limit` at their defaults; raising them risks an oversized result truncated to a file.
   - Emit each query and matching post summaries. If truncated anyway, read via a subagent or state `Mattermost Hub result skipped: <reason>`.
   - If unavailable, state `Mattermost Hub search skipped: <reason>`.
4. Internal Jira (`MM-XXXXX`): the local Jira MCP `mcp__atlassian_local__*` for symptom keywords, Phase 1 error strings, and any `MM-XXXXX` keys surfaced in earlier phases. Emit each query (JQL or tool call) and matching issue keys + summaries. If `mcp__atlassian_local__*` is absent, state `Jira search skipped: <reason>`; do not substitute another Atlassian connector or start an OAuth flow.
5. GitHub issues and PRs per in-scope repo - one search per repo, all repos required:
   - **Preferred:** `mcp__claude_ai_GitHub_MCP__search_issues` and `mcp__claude_ai_GitHub_MCP__search_pull_requests` with symptom keywords and Phase 1 error strings. Emit each query and matching issue/PR titles + numbers.
   - **Fallback 1 (claude.ai GitHub MCP absent):** `mcp__github_local__search_issues` and `mcp__github_local__search_pull_requests`, same queries.
   - **Fallback 2 (no GitHub MCP available):** `WebFetch`/`WebSearch` against `https://github.com/mattermost/<repo>/issues`. Emit the search URL and top result titles + numbers.
   - If no GitHub MCP is available, state `GitHub MCP skipped: <reason>` and use the WebFetch fallback.

If searches 3, 4, or 5 cannot run (offline, WebFetch fails, MCP unavailable, Hub result oversized), state `<search> skipped: <reason>` in the conclusion. Do not omit silently.

Complete this phase before proceeding.

## Phase 7 - Re-validation

Phase 8 is blocked until the leading hypothesis **and at least two named alternatives** each have a visible disprove artefact.

**Leading hypothesis.** Run a query to disprove it.

- For missing/buggy code-path hypotheses, search for the expected fix in the customer's version: absent confirms, present refutes.
- If Step 0 (Phase 5) found codebase-memory available, run `/cbm-search-graph <repo> <symbol>` or `/cbm-query-graph <repo> <cypher>` inline for this search.
- If codebase-memory is unavailable, use `rg`/`grep`/`git` for the artefact.

**Alternative hypotheses (≥2).** Name plausible competitors drawn from the Phase 1 inventory output - candidates not yet ruled out.

- Examples: permissions, license tier, a separate config flag, a different code path.
- No strawmen.

After the leading hypothesis survives re-validation, scan the Phase 6 Hub, GitHub, and Jira results already in
context for the confirmed bug, error string, or fix commit. If a match exists, note it: known issue,
existing workaround, or fix version. No new tool calls required; results are already in context.

Each hypothesis produces an artefact: shell command (`rg`, `fd`, `grep`, `find`, `git`) or Grep/Read/Find call plus a quoted output line (or `no matches`):

```
Re-validation: <hypothesis>; disproved by <command>:
  <quoted output or "no matches">.
```

For code-location questions: `Re-validation: "no alternative definition of <X> exists"; disproved by \`rg --no-ignore --hidden -n '^type <X> ' upstream/<repo>/\` / \`grep -rn '^type <X> ' upstream/<repo>/\`: <output>`. Multiple hits need disambiguation (e.g. struct vs interface).

Complete this phase before proceeding.

## Phase 8 - Conclusion framing

When a customer config issue intersects an upstream defect, state BOTH:

- **Customer remediation:** what to change to unblock (migrate DB, change setting, upgrade).
- **Upstream bug surface:** code-level defect with `file:line` and conditions under which it affects other deployments.

Config-only answer when a defect was found is a framing violation. If no defect found, state: "No upstream defect identified - configuration is out of contract."

**Fragment opportunity (mandatory check).** For each in-scope repo, check whether `fragments/<repo>.md` exists.

- **Missing fragment:** state `Fragment opportunity: fragments/<repo>.md`.
  - List 1-3 reusable patterns from this ticket that belong in it; each with `file:line` or a quoted log line.
  - Offer to create in a follow-up turn; do not auto-create.
- **Fragment exists, pattern not yet captured:** state `Fragment update opportunity: fragments/<repo>.md - <section>` with supporting evidence.

To action any fragment opportunity, run `/fragment-update`.

Complete this phase before proceeding.

## Phase 9 - Analysis log (MANDATORY)

Maintain two files per ticket, **written once, at the end of the pipeline** (not incrementally per phase). Ticket mode only - description mode has no ticket directory, skip.

- `tickets/<ID>/analysis.md` - live current-state view; key sections always reflect the latest understanding.
- `tickets/<ID>/analysis-full.md` - append-driven current-state view; same content as analysis.md, but sections are kept current by appending, not editing in place.

**Runs once**, right after Phase 8's conclusion, same turn: `Write`/`Edit` both files with everything learned across Phases 0-8.

- Never contains drafting/copying narration (e.g. "Drafted + corrected customer reply...", "copied to clipboard") - investigation facts only.

**`analysis.md` maintenance (live view):**

- **Replace in place:** Current hypothesis (move superseded entries to Ruled out with a brief reason), Correlation, Open questions (remove answered; add new), Next steps (replace; don't accumulate stale items).
- **Never delete:** Ruled out entries; only add.
- **Append:** Artifacts reviewed, Evidence collected, Steps and outcomes, Deployment facts as they are confirmed. **Investigated with:** set once; update only if it changes mid-ticket.

**`analysis-full.md` maintenance (chronological log):**

A "session" is one `/investigate` run, not a turn.

Session 1 (creation): both files start identical - same template, same content.
Subsequent sessions: add `---` and `## Session YYYY-MM-DD`, then re-append each section that changed with its full current content (same section names as the template). The bottom-most instance of any section is always the authoritative current state. Never edit earlier entries.

---

## Analysis log template

Section shape for both files on first creation, populated with real content, not left empty:

```markdown
# Ticket <ID> - Analysis

- Investigated with: (model / effort-thinking level, e.g. "Claude Opus 4.8, high"; "Claude Sonnet 5, xhigh". Record model name; effort/thinking level if known or if the operator states it.)
- Ticket type: Fault investigation | Advisory / research (pick one)

## Deployment
- Version:
- Type: single-node | HA (<n> nodes)
- Database:
- Deployment method: (Docker / K8s / bare metal / unknown)

## Timeline

## Artifacts reviewed
- [ ] (list specific files reviewed)
- [ ] (list screenshots or images reviewed)

## Evidence collected

## Reported symptom

## Correlation

## Current hypothesis

## Steps and outcomes

## Ruled out

## Open questions

## Next steps

## Resolution
```

**Advisory / research mapping.** Headings stay identical regardless of `Ticket type` - `resume` and
`search-tickets` key off these exact names. For `Ticket type: Advisory / research` (customer questions,
architecture guidance, no fault to diagnose), map the same headings instead of forcing fault-investigation
phrasing:

- `Reported symptom` -> the question(s) asked.
- `Correlation` -> reasoning connecting evidence to the recommendation.
- `Current hypothesis` -> the recommendation/answer.
- `Ruled out` -> alternatives considered and why rejected.

Sections genuinely not applicable (e.g. `Timeline` for a single-session question) may be written as `N/A`
instead of forced content.
