### mattermost-plugin-msteams

**What**: Microsoft Teams channel-to-channel sync and user account bridge via Microsoft Graph webhooks and OAuth (separate plugin from `mattermost-plugin-msteams-meetings`, which is meetings-only)
**Stack**: Go backend, React frontend
**Plugin ID**: `com.mattermost.msteams-sync`
**Min server**: 10.7.0
**Database**: PostgreSQL / MySQL via SQLStore (`msteamssync_*` tables) + KV fallback for transient OAuth state

**Authentication**:
- OAuth 2.0 with Microsoft Graph (Azure AD app registration: tenant ID, client ID, client secret).
- Token encryption: AES-256 via `EncryptionKey` plugin setting.
- Webhook validation: HMAC-based `WebhookSecret` for inbound Microsoft activity notifications.

**Configuration**:

| Field | Purpose |
|---|---|
| `tenantId` | Azure AD tenant ID |
| `clientId` | OAuth client ID |
| `clientSecret` | OAuth client secret (encrypted) |
| `encryptionKey` | AES key for at-rest token encryption (auto-generated) |
| `webhookSecret` | HMAC secret for validating Teams webhook payloads (auto-generated) |
| `syncNotifications` | Enable chat-message sync notifications (default `true`) |
| `connectedUsersAllowed` | Max users permitted to connect (default `1000`) |
| `connectedUsersRestricted` | Restrict connections to whitelist only (default `false`) |
| `evaluationAPI` | Use Microsoft's evaluation (rate-limited) API (default `false`) |

**Network requirements**:
- Outbound HTTPS to `graph.microsoft.com`.
- Inbound webhooks from Microsoft Teams to `{SiteURL}/plugins/msteams-sync/api/v1/changes` and `/lifecycle`.
- `SiteURL` must be publicly reachable from Microsoft infrastructure.

**Slash commands**:
- `/msteams connect` - link Teams account.
- `/msteams disconnect` - revoke connection.
- `/msteams status` - show connection status.
- `/msteams notifications on|off|status` - control chat-sync notifications.

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Configuration validation | `server/configuration.go` |
| Webhook ingestion + secret check | `server/api.go` (`processActivity`, `ConstantTimeCompare`) |
| OAuth redirect handler | `server/api.go` |
| Connect command | `server/command.go` (`executeConnectCommand`) |
| Activity queue + message sync | `server/handlers.go` (`ActivityHandler`) |
| Token encryption | `server/store/sqlstore/crypt.go` |
| Microsoft Graph client | `server/msteams/client.go` |
| SQL store + migrations | `server/store/sqlstore/` |

### Common Investigation Patterns

**User cannot connect or connection fails**: Verify tenant ID, client ID, and client secret in System Console -> MS Teams settings. The Azure app registration must have delegated permissions granted (`Chat.Read`, `ChatMessage.Read`). Watch logs during `/msteams connect` for OAuth exchange errors. The error "You are already connected to MS Teams. Please disconnect..." means a stale token exists in the store.

**Tenant configuration / missing scopes**: Azure app needs delegated `Chat.Read` / `ChatMessage.Read` plus application-role permissions for global subscriptions. `Insufficient permissions` errors in logs indicate missing scopes. Webhook validation fails if `webhookSecret` is cleared or out-of-sync between cluster nodes.

**Channel sync / message bridging broken**: Webhook payloads validate `ClientState` against `WebhookSecret` (constant-time compare). Mismatch -> `Invalid webhook secret`. Activity queue overflows at 5000 items if handler workers stall. Check that DB migrations 001-009 ran and `msteamssync_*` tables exist. Post linking via `msteamssync_posts`; channel links via `msteamssync_links`.

### MS Teams Plugin Errors

| Error | Cause | Resolution |
|---|---|---|
| `tenant ID should not be empty` | Config incomplete | Set tenant ID in plugin settings |
| `client ID should not be empty` | OAuth app ID missing | Verify Azure app client ID |
| `client secret should not be empty` | OAuth credentials incomplete | Set client secret |
| `encryption key should not be empty` | Encryption key not generated | Generate or set `EncryptionKey` |
| `webhook secret should not be empty` | Webhook validation disabled | Generate `WebhookSecret` |
| `Invalid webhook secret` | Payload `ClientState` mismatch | Verify webhook secret matches Teams subscription config |
| `You cannot connect your account because the maximum limit of users allowed to connect has been reached` | `connectedUsersAllowed` hit | Increase limit or disconnect existing user |
| `This Teams user is already connected to another user on Mattermost` | Email mismatch / duplicate link | Ensure email matches; one Teams user per Mattermost user |
