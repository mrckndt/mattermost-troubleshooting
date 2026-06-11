---
name: blind-triage
description: Orient on a ticket directory and run blind log triage - extract all errors and warnings, anchor to timestamps, resolve AppError keys - before the customer's reported symptom is introduced.
user-invocable: true
---

Apply the Shell conventions from `AGENTS.md` before continuing (verify project-root CWD, capture `PROJECT_ROOT`, use absolute paths).

Args: $ARGUMENTS

Blind triage: survey the artifacts and report what the logs contain. No hypothesis formation. Do not ask for or accept the customer's reported symptom until the end of this command.

## Step 1 - Inventory

Resolve the ticket directory:
- If `$ARGUMENTS` is provided, use `tickets/$ARGUMENTS/`.
- If not, list `tickets/` subdirectories and ask which to triage before proceeding.

List every file recursively under the ticket directory. Attempt to read each artifact. If any file cannot be read or parsed (PDFs, images, compressed archives, unknown formats), stop and report which files are inaccessible and why. Do not proceed until all artifacts are accessible.

## Step 2 - Orient

From the log header, config, or early entries, extract:
- Mattermost version
- Deployment type: single-node or HA; if HA, number of nodes
- Database backend
- Deployment method (Docker / K8s / bare metal / unknown)

If `analysis.md` already exists in the ticket directory, read it and summarize where the investigation currently stands.

Report this orientation summary. Do not form hypotheses yet.

## Step 3 - Extract errors and warnings

From all log files in the ticket directory:

1. Extract every `level=error` and `level=warn` line.
2. Group by `msg` field: deduplicate, count occurrences, and record the **first-seen timestamp** for each group. Count alone is misleading - an error firing 200 times since last Tuesday is a different signal from the same error appearing for the first time at the incident time.
3. Identify time windows where error volume spikes.
4. List separately any errors that appear exactly once - these are often the most diagnostic.
5. For HA deployments: note whether each error class appears on one node or all nodes.
6. Flag anything anomalous, even if seemingly minor or unrelated to an obvious failure.

## Step 4 - AppError verbatim extraction

For every `level=error` line where `msg` contains `"An internal error has occurred"`, or any log entry matching the `<Where>: <Message>` AppError shape:

1. Capture `<Message>` **exactly** as it appears - full punctuation, no paraphrasing, no truncation.
2. Run the lazy auto-refresh on `upstream/mattermost` per the `AGENTS.md` policy, then:
   `grep -F "<message>" "$PROJECT_ROOT/upstream/mattermost/server/i18n/en.json"`
   - One match: record the translation key alongside the error.
   - Multiple matches: record all candidates; disambiguate using `<Where>` and surrounding log context.
   - Zero matches: record as a finding - the error likely comes from a plugin, Enterprise code, or version drift; note it for widened search later.

Do this before forming any hypothesis. Guessing intent from `<Where>` alone has misled prior investigations.

## Step 5 - Present findings

Present a structured triage report:
- Orientation: version, deployment type, artifacts present
- Error/warning inventory: grouped by `msg`, with count and first-seen timestamp
- Time window analysis: when did error volume change?
- Single-occurrence errors (listed separately)
- AppError messages with resolved i18n keys, or "zero matches" noted as a finding
- Any anomalous findings

Do not prioritize, theorize, or propose next steps. Report what the logs contain.

End with: **"What did the customer report, and when did they first notice it?"** - then stop.

## Analysis log

Update `tickets/<name>/analysis.md` and `tickets/<name>/analysis-full.md` per the analysis log rules in `AGENTS.md`. Populate Deployment, Timeline (first-seen timestamps from triage), Artifacts reviewed, and Evidence collected. Leave Current hypothesis and Next steps as stubs - they are for after the symptom is introduced.
