### mattermost-plugin-gitlab

**What**: GitLab integration for Mattermost - notifications, subscriptions, merge request reviews, pipeline status
**Stack**: Go backend, React frontend
**Plugin ID**: `com.github.manland.mattermost-plugin-gitlab`
**Min server**: 10.7.0
**Database**: KV store only (no custom tables)

**Authentication**: OAuth 2.0 with GitLab
- User-level OAuth; tokens encrypted with `EncryptionKey` (AES)
- Supports self-hosted GitLab via `GitlabURL`
- Cloud deployments use Chimera preregistered OAuth proxy
- Supports encryption key rotation via `PreviousEncryptionKey` fallback

**Configuration** (from `server/configuration.go`):

| Field | Default | Purpose |
|---|---|---|
| `GitlabURL` | `https://gitlab.com` | GitLab instance URL |
| `GitlabOAuthClientID` | (required) | GitLab OAuth app client ID |
| `GitlabOAuthClientSecret` | (required) | GitLab OAuth app client secret |
| `WebhookSecret` | (auto-generated) | Webhook validation secret |
| `EncryptionKey` | (auto-generated) | AES key for token encryption |
| `GitlabGroup` | (empty) | Locks plugin to a single GitLab group |
| `EnablePrivateRepo` | `false` | Allow private repository access |
| `EnableCodePreview` | `"public"` | Code preview: `disable`, `public`, `privateAndPublic` |
| `EnableChildPipelineNotifications` | `true` | Notify on child pipeline events |
| `UsePreregisteredApplication` | `false` | Use Chimera preregistered OAuth (Cloud only) |

**Slash commands**: `/gitlab connect`, `/gitlab disconnect`, `/gitlab todo`, `/gitlab subscriptions list|add|delete <owner[/repo]> [features]`, `/gitlab pipelines run [owner]/repo [ref]`, `/gitlab me`, `/gitlab settings [setting] [value]`, `/gitlab webhook list|add|delete <owner[/repo]>`, `/gitlab instance`, `/gitlab about`, `/gitlab help`

**Subscription features**: `issues`, `confidential_issues`, `jobs`, `merges`, `pushes`, `issue_comments`, `merge_request_comments`, `merge_request_assigns`, `pipeline`, `tag`, `pull_reviews`, `label:"name"`, `deployments`, `releases`

**Network requirements**:
- Outbound HTTPS to GitLab instance (`gitlab.com` or custom `GitlabURL`)
- Inbound webhooks from GitLab to `{SiteURL}/plugins/com.github.manland.mattermost-plugin-gitlab/webhook`
- SiteURL required (checked on plugin activation; plugin fails to start without it)

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Config struct and validation | `server/configuration.go` |
| Plugin lifecycle and user data | `server/plugin.go` |
| HTTP API routes | `server/api.go` |
| OAuth flow | `server/oauth.go` |
| Webhook entry point | `server/webhook.go` |
| Webhook type handlers (issue, MR, pipeline, etc.) | `server/webhook/` |
| Slash command handlers | `server/command.go` |

### GitLab Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `siteURL is not set. Please set it and restart the plugin` | Plugin activation failed | Set `ServiceSettings.SiteURL` and restart the plugin |
| `404 {message: 404 Group Not Found}` | Invalid GitLab group in config | Verify `GitlabGroup` value matches an existing GitLab group |
| `404 {message: 404 Project Not Found}` | Invalid project namespace | Verify the owner/repo path exists and user has access |
| `Unable to obtain mutex for KV migration` | KV store access contention | Check server logs for store errors; may resolve on retry |
| `Unable to decrypt token for KV migration` | Encryption key mismatch | If key was rotated, set previous key in `PreviousEncryptionKey` |
| `401 {error: invalid_token}` | Expired/invalid OAuth token | Reconnect: `/gitlab disconnect` then `/gitlab connect` |
| `cannot use pre-registered application if Chimera URL is not set` | Cloud config missing Chimera URL | Non-Cloud deployments should set `UsePreregisteredApplication` to false |
