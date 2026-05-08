### mattermost-plugin-gitlab

**What**: GitLab integration for Mattermost (gitlab.com SaaS and self-hosted) - notifications, channel subscriptions, MR/issue management, pipeline triggers
**Plugin ID**: `com.github.manland.mattermost-plugin-gitlab`
**Min server**: 10.7.0
**Database**: KV store only (no custom tables)

**Authentication**: OAuth 2.0 with GitLab.
- User-level OAuth; tokens encrypted with `EncryptionKey` (AES).
- Self-hosted GitLab supported via `GitlabURL` (any base URL); SaaS uses `https://gitlab.com`.
- Cloud Mattermost deployments may use Chimera preregistered OAuth (`UsePreregisteredApplication=true`); requires `PluginSettings.ChimeraOAuthProxyURL` (or `MM_PLUGINSETTINGS_CHIMERAOAUTHPROXYURL`) and only works against gitlab.com.
- Token re-encryption: when `EncryptionKey` rotates, the previous key is kept transiently as `PreviousEncryptionKey` so reads can fall back while a background re-encryption pass migrates stored tokens.

**Configuration** (from `server/configuration.go` + `plugin.json`):

| Field | Default | Purpose |
|---|---|---|
| `GitlabURL` | `https://gitlab.com` | Base URL of GitLab instance (SaaS or self-hosted) |
| `GitlabOAuthClientID` | (required unless preregistered) | OAuth Application ID |
| `GitlabOAuthClientSecret` | (required unless preregistered) | OAuth Application Secret |
| `WebhookSecret` | (auto-generated) | Validates inbound GitLab webhook payloads via `X-Gitlab-Token` |
| `EncryptionKey` | (auto-generated) | AES key for at-rest token encryption |
| `UsePreregisteredApplication` | `false` | Cloud-only Chimera proxy (gitlab.com only) |
| `GitlabGroup` | (empty) | Restrict plugin usage to a single GitLab group |
| `EnablePrivateRepo` | `false` | Allow subscriptions to private projects |
| `EnableChildPipelineNotifications` | `true` | Post notifications for child pipelines |
| `EnableCodePreview` | `public` | Permalink expansion: `disable` / `public` / `privateAndPublic` |

**Network requirements**:
- Outbound HTTPS to `GitlabURL` (API + OAuth).
- Inbound webhooks from GitLab to `{SiteURL}/plugins/com.github.manland.mattermost-plugin-gitlab/webhook`.
- SiteURL must be reachable from GitLab; mismatched OAuth callback (must be `{SiteURL}/plugins/com.github.manland.mattermost-plugin-gitlab/oauth/complete`) fails the connect flow.
- Webhook secret check is a plain string compare against the `X-Gitlab-Token` header (`server/webhook.go:67`) - no HMAC.

**Slash commands** (`server/command.go`): `/gitlab connect`, `/gitlab disconnect`, `/gitlab todo`, `/gitlab me`, `/gitlab settings [setting] [value]`, `/gitlab subscriptions list|add|delete`, `/gitlab webhook list|add`, `/gitlab pipelines run|trigger`, `/gitlab issue create`, `/gitlab instance install|uninstall|list|default|alias|unalias`, `/gitlab setup`, `/gitlab help`, `/gitlab about`.

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Config struct + validation | `server/configuration.go` |
| OAuth + HTTP API handlers | `server/oauth.go`, `server/api.go`, `server/plugin.go` |
| Webhook ingestion + secret check | `server/webhook.go` |
| Webhook event handlers (per type) | `server/webhook/` (issue, merge_request, pipeline, push, jobs, tag, release, deployment) |
| Slash command handlers | `server/command.go` |
| Channel subscriptions | `server/subscriptions.go`, `server/subscription/` |
| Multi-instance management | `server/instance.go` |
| Token re-encryption (background) | `server/reencrypt_test.go`, `server/configuration.go` (`PreviousEncryptionKey`) |
| Chimera proxy logic | `server/plugin.go` (search `chimera`) |
| GitLab API client wrapper | `server/gitlab/` (api.go, gitlab.go, user.go, webhook.go, pipeline.go) |

### Common Investigation Patterns

**OAuth callback / redirect mismatch**: The OAuth Application's redirect URI must be exactly `{SiteURL}/plugins/com.github.manland.mattermost-plugin-gitlab/oauth/complete`. Self-hosted GitLab installs need the OAuth Application created in **Admin Area > Applications** (or user-level Applications) and `GitlabURL` pointed at the same host. `UsePreregisteredApplication=true` is rejected when `GitlabURL` is not `https://gitlab.com` (`server/configuration.go:137`).

**Webhook secret mismatch (`X-Gitlab-Token` doesn't match `WebhookSecret`)**: Inbound webhook is silently dropped. Recreate the webhook in GitLab (Project / Group **Settings > Webhooks**) using the secret printed by `/gitlab webhook add` or visible in plugin settings. The plugin offers `/gitlab webhook add owner[/repo] [options] [url] [token]` to provision the webhook server-side via the user's OAuth token. Note: GitLab webhooks use a plain "Secret token" header compare, not HMAC.

**Self-hosted GitLab + private repos**: Subscriptions to private projects fail with permission errors unless `EnablePrivateRepo=true` AND the connected user's OAuth token has the `api` scope. The OAuth Application in self-hosted GitLab must include `api` (and `read_user`) scopes.

**Chimera unreachable on Cloud**: `UsePreregisteredApplication=true` requires `PluginSettings.ChimeraOAuthProxyURL` set on the server. Self-hosted Mattermost installations should leave this off and register a custom GitLab OAuth Application instead - on-prem the plugin logs an explicit warning if Chimera is requested without a proxy URL configured (`server/plugin.go:111`).

**Encryption key rotated, users get token errors**: GitLab plugin handles this gracefully via `PreviousEncryptionKey` + background re-encryption (`server/configuration.go`, `server/reencrypt_test.go`). If users still see persistent decrypt errors hours after a rotation, the background pass failed - have affected users `/gitlab disconnect` then `/gitlab connect`.

**Multi-instance gotcha**: The plugin supports multiple GitLab instances simultaneously (`/gitlab instance install <URL>`, `/gitlab instance default <URL>`). Subscriptions, webhooks, and `/gitlab me` are scoped to whichever instance the user is connected to. If a user reports "my command is hitting the wrong GitLab", check `/gitlab instance list`.

### GitLab Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `must have a valid GitLab URL` | `GitlabURL` empty or unparseable | Set a full URL with scheme |
| `must have a GitLab oauth client id` | `GitlabOAuthClientID` not set (and not using Chimera) | Create an OAuth Application in GitLab and set the ID |
| `must have a GitLab oauth client secret` | `GitlabOAuthClientSecret` not set | Set the secret from the OAuth Application |
| `pre-registered application can only be used with official public GitLab` | `UsePreregisteredApplication=true` with non-gitlab.com `GitlabURL` | Disable the toggle; register a custom OAuth Application |
| `must have an encryption key` | `EncryptionKey` empty | Auto-generated on save - re-save plugin settings |
| `Unable to create webhook. The Mattermost Site URL is not set.` | `ServiceSettings.SiteURL` empty when running `/gitlab webhook add` | Set SiteURL or pass an explicit URL to `/gitlab webhook add` |
| Webhook silently ignored, no logs | `X-Gitlab-Token` doesn't match `WebhookSecret` | Reconfigure the GitLab webhook with the correct secret |
| `404 {message: 404 Group Not Found}` / `404 Project Not Found` | User token can't see the group/project, or wrong namespace | Verify access; for private projects also check `EnablePrivateRepo` |
