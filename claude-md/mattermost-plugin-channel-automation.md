### mattermost-plugin-channel-automation

**What**: Rules-based automation engine that triggers actions on channel events (message posts, membership changes, schedules, channel creation, user joins)
**Stack**: Go backend, React frontend
**Plugin ID**: `com.mattermost.channel-automation`
**Min server**: 6.2.1
**License**: Enterprise
**Database**: KV store (durable work queue; no direct SQL tables)

**Configuration**:

| Field | Default | Purpose |
|---|---|---|
| `MaxConcurrentFlowsLimit` | `4` | Max concurrent flow executions per plugin instance (requires restart). |
| `MaxFlowsPerChannelLimit` | `0` | Max flows targeting one channel; `0` = unlimited. |
| `EnableUI` | `false` | Show Channel Automation menu in webapp. |
| `AutomationInstructionsURL` | (empty) | User-facing docs URL appended to API instructions for agents/MCP. |

**Triggers**: `message_posted` (channel + optional thread replies), `schedule` (recurring interval >= 1h), `membership_changed` (join/leave), `channel_created` (public channels), `user_joined_team` (with optional user-type filter).

**Actions**: `send_message` (with thread / bot-as support), `ai_prompt` (agent or service completion via Mattermost Agents bridge).

**Slash commands**: none. The plugin exposes a REST API at `/plugins/com.mattermost.channel-automation/api/v1` (flows CRUD, executions history).

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Flow execution engine | `server/flow/executor.go` |
| Trigger matching logic | `server/flow/trigger.go` |
| Action handlers | `server/flow/action/` |
| Trigger / action registry | `server/flow/handler.go` |
| Work queue + concurrency | `server/workqueue/worker.go`, `server/workqueue/store.go` |
| Failure notifications (DM creator, 1h cooldown) | `server/flow/notifier/notifier.go` |
| Permission checks | `server/permissions/check.go` |
| Template rendering (Go text/template) | `server/flow/action/template.go` |

### Common Investigation Patterns

**Rules not firing**: Verify the trigger matches the event (channel IDs, user types, schedule times in UTC). Confirm the flow is enabled. Inspect history via `/flows/{flow_id}/executions`. If `MaxFlowsPerChannelLimit` is set, confirm no other flows already occupy the limit (`server/flow/store.go` `GetFlowIDsForChannel`).

**Template rendering failures**: Validate Go `text/template` syntax in action fields (e.g. `{{.Trigger.Post.Message}}`, `{{(index .Steps "<action_id>").Message}}`). Errors `failed to parse template` / `failed to execute template` indicate syntax errors or missing context keys. Sensitive fields (email, password, auth) are stripped from context; nickname is unavailable.

**Permission errors**: `send_message` requires the flow creator to have `PermissionCreatePost` on the target channel. `ai_prompt` requires the Agents plugin to be active. `channel_created` flows require team-admin on the team; other flows require channel-admin on all literal channel references. System admins bypass these checks.

**Performance with many rules**: `MaxConcurrentFlowsLimit` caps execution goroutines per instance - increase if flows queue. Work items persist in KV store with a 30s poll interval. Cluster-wide coordination uses a flow-index mutex to prevent race conditions. Watch execution history for slow / hung flows.

### Channel Automation Errors

| Error | Cause | Notes |
|---|---|---|
| `agents plugin is not installed or active` | `ai_prompt` triggered without Agents plugin | Install / enable `mattermost-plugin-agents` |
| `missing required config key "prompt"` / `"provider_type"` / `"provider_id"` | Incomplete `ai_prompt` action config | Set all three fields |
| `failed to render template: ...` | Bad Go template syntax | Check brackets, function notation, context-key names |
| `does not have permission to post in channel` | Flow creator lacks `PermissionCreatePost` | Make creator a channel admin or higher |
| `Enterprise license required` | License check fails on `OnActivate` | Plugin requires Enterprise |
| `exactly one trigger type must be set` | Multiple or zero trigger types in flow | Pick exactly one |
| `schedule trigger interval must be at least 1h` | Interval < 60 min | Min supported interval is 1h |
| `failed to get post ... for reply` | `reply_to_post_id` template renders a non-existent post ID | Verify post exists and bot can access it |
