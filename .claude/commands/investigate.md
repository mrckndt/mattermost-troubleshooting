---
description: Run the full investigation pipeline for a ticket or problem description. Enforces tiered query order (fragments → source → docs), scope inference, version alignment, re-validation, and analysis log maintenance.
argument-hint: <ticket-ID> | "<problem description>"
---

Apply the Shell conventions from `CLAUDE.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

**Complete each phase in order. Do not skip ahead, form hypotheses, or run source searches until the phase explicitly permits it.**

- No hypotheses until Phase 1's inventory output (severity table, distinct-msg sweep, error-families list) is in the conversation.
- After any Tier 2 hit, re-check the error-families list for unexplained entries before narrowing.

## Phase 0 - Setup and argument resolution

Determine mode:
- If `$ARGUMENTS` matches a directory under `tickets/` (check with `ls "$PROJECT_ROOT/tickets/$ARGUMENTS"` or similar): **ticket mode** - set `<ID>=$ARGUMENTS`.
- Otherwise: **description mode** - the argument is a problem description. Skip Phase 1 and the Version-alignment file-based detection in Phase 3; proceed using the description as the only input.

If no argument is provided, list `tickets/` subdirectories and ask which ticket to investigate before proceeding.

Initialize the analysis log (ticket mode only): if `tickets/<ID>/analysis.md` does not exist, create it with the template at the bottom of this file. If `tickets/<ID>/analysis-full.md` does not exist, create it with the same template. Stubs only at this point.

Complete this phase before proceeding.

## Phase 1 - Ticket file inventory

Before scope inference, list every file in `tickets/<ID>/` with sizes, then read each one before forming any hypothesis:

```
ls -lh tickets/<ID>/
```

- Files under 500 KB: read in full.
- Files 500 KB and above: read head (first 500 lines) + tail (last 500 lines) + grep for `error`, `warn`, `fatal`, `crash`, `panic`, `exception`.

Do not begin scope inference until all files have been inventoried this way.

### Inventory output (required)

For every log file in `tickets/<ID>/`, emit a fenced block containing:

- **Path and size**
- **Severity counts** (one row per pattern; use `rg -c -e <pattern>` so zero counts still print):
  - `error`, `warn`, `fatal`, `crash`, `panic`, `exception`, `failed`, `timeout`, `denied`, `disabled`, `unauthorized`, `invalid`
- **Distinct messages:** `rg -o '"msg":"[^"]+"' <file> | sort -u | head -50`. Non-JSON logs: swap for `level=<level> msg="<text>"`.
- **First/last error window:** timestamps of the first and last `level=error` line.

After the per-file blocks, emit a combined **error families** list: distinct error-level `msg` values across all log files, deduped.

**Rule:** Phase 2 cannot start until this inventory output is in the conversation. No in-scope repos or hypotheses before that point.

Complete this phase before proceeding.

## Phase 2 - Scope inference

After the file inventory, identify in-scope repos and fragments by judgment first (anything mentioned or implied by symptoms); the table below is a backstop for keywords and multi-repo families. Don't anchor to it - unlisted repos must still surface.

| Signal in ticket / logs | Repos / fragments |
|---|---|
| desktop, Electron, macOS, Windows, Linux, server tab, deep link, GPO, MDM, Group Policy | `desktop` |
| Docker, docker-compose | `docker` |
| mobile, push notification, iOS, Android, React Native, push proxy, TestFlight, certificate pinning, WatermelonDB, MPNS | `mattermost-mobile` |
| Helm, operator, ingress, MinIO, Kubernetes, K8s, EKS, CRD, Cluster | `mattermost-operator`, `mattermost-helm` |
| AI, Agents, Copilot, LLM, OpenAI, Anthropic, AWS Bedrock, Google Gemini, Ollama, MCP, pgvector, semantic search, RAG | `mattermost-plugin-agents` |
| Boards, Focalboard, kanban, tasks | `mattermost-plugin-boards` |
| calls, meeting, voice calling, screen sharing, WebRTC, ICE, STUN, TURN, SFU, NAT, TURN credentials, IPv6, packet loss, RTCD, recording, transcription, transcript, job service, recording job, transcribing job, ffmpeg, Chromium, Xvfb | `mattermost-plugin-calls`, `rtcd`, `calls-offloader`, `calls-recorder`, `calls-transcriber` |
| channel automation, flow, workflow, trigger, schedule | `mattermost-plugin-channel-automation` |
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

**Detect plugin versions** (when plugins are in scope):
- `tickets/<ID>/plugins.json` - `version` field per plugin entry
- `tickets/<ID>/mattermost.log` - bottom-most `"Installing extracted plugin"` line per `plugin_id`. Earlier installs were superseded by upgrades or rollbacks.
- Example: `rg "Installing extracted plugin" mattermost.log | rg <plugin_id> | tail -1`

**Align repos:**

For `mattermost` and `enterprise`: release branches are `release-X.Y`; patch tags are `vX.Y.Z`. Ref resolution:
- Exact version known: `vX.Y.Z` tag
- Minor version only: `release-X.Y` branch; a pulled branch reflects the latest patch
- Current main: `git -C "$PROJECT_ROOT/upstream/<repo>" symbolic-ref refs/remotes/origin/HEAD --short`

1. For each in-scope repo, check current ref:
   ```
   git -C "$PROJECT_ROOT/upstream/<repo>" describe --tags --exact-match 2>/dev/null || \
     git -C "$PROJECT_ROOT/upstream/<repo>" rev-parse --abbrev-ref HEAD
   ```
2. If the ref does not match the customer's version, run `/git-switch <repo> <ref>`.
3. Run `/git-pull` if on a branch; skip if on a tag (detached HEAD - tags are immutable).
4. After the investigation completes, state which version(s) the analysis was run against (mirroring the unknown-version footer).

**Unknown version:** stay on the current ref and proceed. After the investigation completes, state: "Server version unknown; analysis run against `<current-ref>`." Ask whether to re-run against a specific version or `main`. Apply the same note for any plugin repos in scope.

Complete this phase before proceeding.

## Phase 4 - Query order

Run in order on every turn. No early stopping. Do not interpret or form hypotheses until all tiers are complete.

### Tier 1 - `claude-md/<repo>.md` fragments

Read fragments for all inferred repos.

Complete this tier before proceeding.

### Tier 2 - source code

**Phase 1: AppError → i18n key lookup.**
- Applies only to Mattermost server logs; skip if none present.
- Identify server logs by filename (`mattermost.log`, `*mattermost*.log`, `*mattermost*.txt`) or by content (lines matching `level=(error|warn|info|debug).*msg=`).
- `<Message>` in `<Where>: <Message>` is almost always a translation key value - grepping it returns the precise call-site key.

1. Identify server language from the server log; check `ls upstream/mattermost/server/i18n/` for `<lang>.json`.
2. For any `level=error` line where `msg` is the localized "internal error" string, or any AppError-shaped string `<Where>: <Message>`, extract `<Message>` **exactly** - full punctuation, no paraphrasing, no truncation.
3. `grep -F "<message>" upstream/mattermost/server/i18n/<lang>.json` to get the key; grep source for the call site.

**Phase 2: Source search.** Always run against `upstream/mattermost/`, `upstream/enterprise/` (if cloned; may be absent if GitHub SSH key not configured), and all other inferred repos.
AppError i18n matches provide a direct, reliable call-site path; full source search gives the complete picture regardless.

4. Search all inferred repos by config key, function name, feature area, or symptom keyword using `rg`/`grep`/`fd`/Read/Find.

Complete this tier before proceeding.

### Tier 3 - product docs, developer docs, upstream issues

Search all three unconditionally:
- `upstream/docs/source/` (product docs, customer-facing). Example: `grep -rn "MaxOpenConns" upstream/docs/source/`
- `upstream/mattermost-developer-documentation/site/content/` (developer docs). Example: `grep -rn "plugin manifest" upstream/mattermost-developer-documentation/site/content/`
- `https://github.com/mattermost/<repo>/issues` per in-scope repo via `WebFetch`/`WebSearch`. Emit the search URL and top result titles + numbers.

If the issues search cannot run (offline, WebFetch fails), state `upstream issues check skipped: <reason>` in the conclusion. Do not omit silently.

Complete this tier before proceeding.

## Phase 5 - Re-validation

Phase 6 is blocked until the leading hypothesis **and at least two named alternatives** each have a visible disprove artefact.

**Leading hypothesis.** Run a query to disprove it.

- For missing/buggy code-path hypotheses, search for the expected fix in the customer's version: absent confirms, present refutes.

**Alternative hypotheses (≥2).** Name plausible competitors drawn from the Phase 1 inventory output - candidates not yet ruled out.

- Examples: permissions, license tier, a separate config flag, a different code path.
- No strawmen.

Each hypothesis produces an artefact: shell command (`rg`, `fd`, `grep`, `find`, `git`) or Grep/Read/Find call plus a quoted output line (or `no matches`):

```
Re-validation: <hypothesis>; disproved by <command>:
  <quoted output or "no matches">.
```

For code-location questions: `Re-validation: "no alternative definition of <X> exists"; disproved by \`grep -rn '^type <X> ' upstream/<repo>/\`: <output>`. Multiple hits need disambiguation (e.g. struct vs interface).

## Phase 6 - Conclusion framing

When a customer config issue intersects an upstream defect, state BOTH:

- **Customer remediation:** what to change to unblock (migrate DB, change setting, upgrade).
- **Upstream bug surface:** code-level defect with `file:line` and conditions under which it affects other deployments.

Config-only answer when a defect was found is a framing violation. If no defect found, state: "No upstream defect identified - configuration is out of contract."

**Fragment opportunity (mandatory check).** For each in-scope repo, check whether `claude-md/<repo>.md` exists.

- **Missing fragment:** state `Fragment opportunity: claude-md/<repo>.md`.
  - List 1-3 reusable patterns from this ticket that belong in it; each with `file:line` or a quoted log line.
  - Offer to create in a follow-up turn; do not auto-create.
- **Fragment exists, pattern not yet captured:** state `Fragment update opportunity: claude-md/<repo>.md - <section>` with supporting evidence.

## Phase 7 - Analysis log (MANDATORY)

Maintain two files per ticket. Highest-priority task - above drafting replies, clipboard, or closing the loop.

- `tickets/<ID>/analysis.md` - live current-state view; key sections always reflect the latest understanding.
- `tickets/<ID>/analysis-full.md` - append-driven current-state view; same content as analysis.md, but sections are kept current by appending, not editing in place.

**Fires on:** any turn that references, reads, or discusses a `tickets/<ID>/` directory (lookups, clipboard, follow-ups); when a symptom matches a known ticket folder's evidence family; or when a finding refines or disproves a hypothesis in any prior ticket's analysis files.

**How to apply:**

1. First or last tool calls on any ticket-touching turn must be `Write`/`Edit` to both files.
2. Never defer - stale-by-one-turn is a violation.

**`analysis.md` maintenance (live view):**

- **Replace in place:** Current hypothesis (move superseded entries to Ruled out with a brief reason), Correlation, Open questions (remove answered; add new), Next steps (replace; don't accumulate stale items).
- **Never delete:** Ruled out entries; only add.
- **Append:** Artifacts reviewed, Evidence collected, Steps and outcomes, Deployment facts as they are confirmed.

**`analysis-full.md` maintenance (chronological log):**

Session 1 (creation): both files start identical - same template, same content.
Subsequent sessions: add `---` and `## Session YYYY-MM-DD`, then re-append each section that changed with its full current content (same section names as the template). The bottom-most instance of any section is always the authoritative current state. Never edit earlier entries.

---

## Analysis log template

Stubs if empty; use for both files on creation:

```markdown
# Ticket <ID> - Analysis

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
