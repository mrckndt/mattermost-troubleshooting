### mattermost-plugin-github

**What**: GitHub integration for Mattermost (SaaS and Enterprise) - notifications, subscriptions, PR/issue management
**Stack**: Go backend, React frontend, custom GraphQL client for GitHub API
**Plugin ID**: `github`
**Min server**: 10.7.0
**Database**: KV store only (no custom tables)

**Authentication**: OAuth 2.0 with GitHub
- User-level OAuth; tokens encrypted with `EncryptionKey` (AES)
- Supports GitHub Enterprise via `EnterpriseBaseURL`/`EnterpriseUploadURL`
- Cloud deployments use Chimera preregistered OAuth proxy
- Automatic token refresh on 401 errors

**Configuration** (from `server/plugin/configuration.go`):

| Field | Default | Purpose |
|---|---|---|
| `GitHubOAuthClientID` | (required) | GitHub OAuth app client ID |
| `GitHubOAuthClientSecret` | (required) | GitHub OAuth app client secret |
| `WebhookSecret` | (required, auto-generated) | GitHub webhook HMAC SHA1 validation |
| `EncryptionKey` | (required, auto-generated) | AES key for token encryption |
| `GitHubOrg` | (empty) | Comma-separated allowed GitHub orgs |
| `EnterpriseBaseURL` | (empty) | GitHub Enterprise base URL |
| `EnterpriseUploadURL` | (empty) | GitHub Enterprise upload URL |
| `UsePreregisteredApplication` | `false` | Use Chimera preregistered OAuth (Cloud only) |
| `EnablePrivateRepo` | `false` | Allow private repository access |
| `ConnectToPrivateByDefault` | `false` | Auto-enable private repos on connect |
| `EnableCodePreview` | `"public"` | Code preview: `disable`, `public`, `privateAndPublic` |
| `EnableWebhookEventLogging` | `false` | Log webhook events (requires DEBUG log level) |
| `EnableLeftSidebar` | `true` | Show notification counters in left sidebar |
| `ReviewTargetDays` | `0` | PR review SLA in days (0 = disabled) |
| `OverdueReviewsChannelID` | (empty) | Channel for daily overdue review alerts |
| `ShowAuthorInCommitNotification` | `false` | Include commit author in commit notifications |
| `GetNotificationForDraftPRs` | `false` | Send notifications for draft pull requests |

**Slash commands**: `/github connect`, `/github disconnect`, `/github subscribe <repo>`, `/github unsubscribe <repo>`, `/github todo`, `/github me`, `/github settings`, `/github mute`, `/github issue [new <repo>]`, `/github default-repo <repo>`, `/github about`, `/github help`. Admin-only: `/github setup` (handled separately from the standard command map; first-run OAuth setup wizard).

**Network requirements**:
- Outbound HTTPS to GitHub API (`api.github.com` or Enterprise URL)
- Inbound webhooks from GitHub to `{SiteURL}/plugins/github/webhook`
- SiteURL required for OAuth callback redirect
- Webhook signature uses HMAC SHA1

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Config struct and validation | `server/plugin/configuration.go` |
| HTTP API routes and OAuth flow | `server/plugin/api.go` |
| Webhook handling and signature verification | `server/plugin/webhook.go` |
| Slash command handlers | `server/plugin/command.go` |
| Channel subscriptions | `server/plugin/subscriptions.go` |
| Review SLA tracking | `server/plugin/review_sla.go`, `server/plugin/sla_digest.go` |
| Token auto-refresh | `server/plugin/mm_34646_token_refresh.go` |

### GitHub Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `must have a github oauth client id` | Missing OAuth client ID | Set `GitHubOAuthClientID` in plugin settings |
| `must have a github oauth client secret` | Missing OAuth client secret | Set `GitHubOAuthClientSecret` in plugin settings |
| `must have an encryption key` | No encryption key configured | Generate key in System Console or set in config |
| `cannot use pre-registered application with GitHub enterprise` | Config conflict | Disable `UsePreregisteredApplication` when using Enterprise URLs |
| `401 Bad credentials` | Invalid or expired OAuth token | Reconnect: `/github disconnect` then `/github connect` |
| `Invalid webhook signature` | Webhook secret mismatch | Reconfigure webhook in GitHub with secret from plugin settings |
| `github user not found` | User not connected to GitHub | Run `/github connect` to initiate OAuth flow |
