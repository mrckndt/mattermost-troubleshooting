### mattermost-plugin-jira

**What**: Two-way Jira integration (Server, Cloud, Data Center)
**Stack**: Go backend, React frontend
**Plugin ID**: `jira`
**Min server**: 10.7.0
**Database**: KV store via Mattermost plugin API (no direct SQL tables)

**Authentication**:
- Jira Cloud: OAuth 2.0
- Jira Server/Data Center: Application Link (consumer key/secret)

**Slash commands** (handlers in `server/command.go`): `/jira instance install|uninstall [server|cloud|cloud-oauth] [URL]`, `/jira connect`, `/jira disconnect`, `/jira subscribe list|edit`, `/jira transition`, `/jira assign`, `/jira webhook`, `/jira help`. Note: `/jira create` is a UI/HTTP flow (`/create-issue` route), not a slash-command handler; plain `/jira subscribe` (no subcommand) defaults to help.

**Key troubleshooting areas**:
- SiteURL must be reachable from Jira (webhooks POST to Mattermost)
- XSRF token expiration during setup flow
- Webhook secret validation failures
- OAuth token/connection staleness
- `AdminAPIToken` + `AdminEmail` required for autolink and event notifications
- API tokens encrypted at rest with plugin-managed key (`EncryptionKey` setting)

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Webhook handling | `server/webhook*.go` |
| Instance management | `server/instance*.go` |
| Channel subscriptions | `server/subscribe.go` |
| OAuth / setup flow | `server/setup_flow.go` |
| KV store layer | `server/kv.go` |
| Slash command handlers | `server/command.go` |

### Common Investigation Patterns

**Webhooks not firing (Jira -> Mattermost)**: Verify `ServiceSettings.SiteURL` is reachable from Jira (especially Jira Cloud). Inbound URL is `{SiteURL}/plugins/jira/api/v2/webhook`. If Mattermost is behind a reverse proxy, ensure POSTs to that path aren't being blocked. Webhook secret mismatch produces `Webhook secret validation failed`.

**OAuth token / connection stale**: After password resets or long inactivity. User runs `/jira disconnect` then `/jira connect`. For Jira Server (Application Link), the consumer key/secret pair on Jira's side must match what the plugin generated.

**Instance not installed**: `/jira instance install` was never run, or the install pointed at the wrong URL. Verify with `/jira instance list`. For Jira Cloud OAuth, `cloud-oauth` is the preferred install variant; legacy `cloud` Atlassian Connect is being phased out.

### Jira Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| Webhooks not firing | Jira cannot reach Mattermost SiteURL | Verify SiteURL is reachable from Jira server/cloud |
| XSRF token expired | Session timeout during setup | Reconnect Jira account via `/jira connect` |
| OAuth token stale | User connection expired | Disconnect and reconnect: `/jira disconnect` then `/jira connect` |
| Webhook secret validation failed | Mismatched webhook secret | Reconfigure webhook in Jira with correct secret from `/jira webhook` |
