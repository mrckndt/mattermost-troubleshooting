### mattermost-plugin-github

**What**: GitHub integration for Mattermost (SaaS and Enterprise) - notifications, subscriptions, PR/issue management
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

**Slash commands** (autocomplete list per `server/plugin/command.go:140`): `/github connect`, `/github disconnect`, `/github subscriptions add|list|delete <repo>`, `/github unsubscribe <repo>`, `/github todo`, `/github me`, `/github settings`, `/github mute`, `/github issue create [text]`, `/github default-repo <repo>`, `/github help`, `/github about`. Admin setup wizard: `/github setup` with subcommands `oauth`, `webhook`, `announce` (run individually if you want to redo a step).

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

### Common Investigation Patterns

**OAuth redirect mismatch**: GitHub rejects the callback. The OAuth app's "Authorization callback URL" must be exactly `{SiteURL}/plugins/github/oauth/complete`. If using GitHub Enterprise, `EnterpriseBaseURL` must be set AND `UsePreregisteredApplication` must be off (Chimera is Cloud-only).

**Webhook secret mismatch (`Invalid webhook signature`)**: Reconfigure the webhook in GitHub with the secret printed by the plugin's settings. Webhook signature uses HMAC SHA1.

**Refresh token rotation issues**: Tokens auto-refresh on 401. If users see persistent `401 Bad credentials`, the refresh token has been revoked (often by GitHub re-authentication). They must `/github disconnect` then `/github connect`.

**Pre-existing `github` username clobbers bot tagging**: if a Mattermost user account named `github` already exists when the plugin tries to create its bot, the plugin uses that user account and posts won't carry a BOT tag. Fix per the admin doc: either `mmctl user convert github --bot` to convert it, or rename the existing account and let the plugin create a fresh `github` bot on next start (requires `EnableBotAccountCreation=true`). Source: `upstream/docs/source/integrations-guide/github.rst:102-105`.

**SLA digest stuck day-marker** (digest configured but not posting): the digest checks a KV key `github_sla_digest_local_day` storing the last day a digest was posted. If that marker matches today's date, the scheduler skips. Source: `server/plugin/sla_digest.go:24-99`.

To force a fresh digest run:
1. Confirm `OverdueReviewsChannelID` and `ReviewTargetDays > 0` in plugin config (otherwise the scheduler short-circuits).
2. Confirm `AdminAPIToken` + `AdminEmail` are set (the digest's GraphQL fetch needs the admin/service-user credentials).
3. Manually delete the KV key `github_sla_digest_local_day`.
4. The 5-minute scheduler will retry on its next tick.

If the scan itself fails (no service user, all orgs fail GraphQL), the day marker is **not** advanced - the 5-minute scheduler keeps retrying within the same day instead of skipping until tomorrow.

**OAuth token auto-refresh log signatures** (MM-34646 cluster task, opt-in, leader-only): success log `Updated user access token for MM-34646` (DEBUG, with `user_id`) at `server/plugin/mm_34646_token_refresh.go:122`. Permission failure: `failed check whether MM-34646 refresh is already done` (line 30). If users still get persistent `401 Bad credentials` after this task has run, the GitHub-side refresh token has been revoked - they must `/github disconnect` then `/github connect`.

**Webhook secret regeneration is one-shot**: per the admin doc, the plugin shows the webhook secret only once after generation (same applies to the encryption key). If a customer "lost the secret", the only path is regenerate -> update both sides per `CLAUDE.md > Plugin token & webhook operations`. Reference: `upstream/docs/source/integrations-guide/github.rst:67`.

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
