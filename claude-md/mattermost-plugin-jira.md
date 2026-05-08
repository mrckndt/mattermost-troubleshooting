### mattermost-plugin-jira

**What**: Two-way Jira integration (Server, Cloud, Data Center)
**Plugin ID**: `jira`
**Min server**: 10.7.0
**Database**: KV store via Mattermost plugin API (no direct SQL tables)

**Authentication**:
- Jira Cloud: OAuth 2.0
- Jira Server/Data Center: Application Link (consumer key/secret)

**Slash commands** (handlers in `server/command.go`):
- Setup: `/jira setup` (interactive wizard - recommended first-time path), `/jira instance install <server|cloud-oauth> <URL>`, `/jira instance uninstall <server|cloud-oauth> <URL>`. The legacy `cloud` (Atlassian Connect / JWT) variant is still recognised for migration but is no longer in the public docs.
- Connection: `/jira connect`, `/jira disconnect`, `/jira info`.
- Issues: `/jira issue create [text]`, `/jira issue view <key>`, `/jira issue assign <key> <user>`, `/jira issue transition <key> <state>`, `/jira issue unassign <key>`.
- Subscriptions: `/jira subscribe` (channel-scoped UI), `/jira subscribe list`, `/jira subscribe edit`.
- Admin: `/jira instance list`, `/jira instance alias <URL> <name>`, `/jira instance unalias <name>`, `/jira instance v2 <URL>` (legacy v2 mode), `/jira webhook [--instance=<URL>]`, `/jira stats`, `/jira v2revert`.
- `/jira create` (issue creation from a post) is a UI/HTTP flow (`/create-issue` route), not a slash-command handler.

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

**Webhooks not firing (Jira -> Mattermost)**: Verify `ServiceSettings.SiteURL` is reachable from Jira (especially Jira Cloud). Inbound URL: modern firehose at `{SiteURL}/plugins/jira/api/v2/webhook`; legacy per-channel webhook at `{SiteURL}/plugins/jira/webhook?secret=...&team=...&channel=...`. If Mattermost is behind a reverse proxy, ensure POSTs to that path aren't being blocked. Webhook secret mismatch produces `Webhook secret validation failed` - rotate per the runbook in `CLAUDE.md > Plugin token & webhook operations` (admin doc: "How do I handle credential rotation for the Jira webhook?" in `upstream/docs/source/integrations-guide/jira.rst`).

**OAuth token / connection stale**: After password resets or long inactivity. User runs `/jira disconnect` then `/jira connect`. For Jira Server (Application Link), the consumer key/secret pair on Jira's side must match what the plugin generated.

**Instance not installed / wrong install variant**: `/jira instance install` was never run, or pointed at the wrong URL. Verify with `/jira instance list`. Public docs only list `server` (Server/DC) and `cloud-oauth` (Cloud); the legacy `cloud` JWT variant is no longer documented. Installing `cloud-oauth` over an existing `cloud` JWT instance carries the saved instance over so existing connections keep working (`server/instance_cloud_oauth_migration_test.go`).

### Jira Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| Webhooks not firing | Jira cannot reach Mattermost SiteURL | Verify SiteURL is reachable from Jira server/cloud |
| XSRF token expired | Session timeout during setup | Reconnect Jira account via `/jira connect` |
| OAuth token stale | User connection expired | Disconnect and reconnect: `/jira disconnect` then `/jira connect` |
| Webhook secret validation failed | Mismatched webhook secret | Reconfigure webhook in Jira with correct secret from `/jira webhook` |
| `WebHooks can only use standard http and https ports (80 or 443)` | Mattermost SiteURL uses a non-standard port | Set up a reverse proxy on 80/443 in front of Mattermost - Jira refuses non-standard webhook ports |
