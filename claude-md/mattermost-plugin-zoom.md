### mattermost-plugin-zoom

**What**: Zoom audio and video conferencing integration for Mattermost
**Plugin ID**: `zoom`
**Min server**: 10.7.0
**Database**: KV store only (no custom tables)

**Authentication**: OAuth 2.0 with Zoom
- User-level: individual users connect via `/zoom connect`
- Account-level: single admin authenticates for all users (`AccountLevelApp` setting); other users matched by Mattermost email
- OAuth tokens encrypted at rest with `EncryptionKey` (AES)

**Configuration** (from `server/configuration.go`):

| Field | Default | Purpose |
|---|---|---|
| `ZoomURL` | `https://zoom.us` | Base Zoom URL (for self-hosted Zoom) |
| `ZoomAPIURL` | `https://api.zoom.us/v2` | Zoom API endpoint |
| `AccountLevelApp` | `false` | Single admin auth for all users |
| `OAuthClientID` | (required) | Zoom OAuth app client ID |
| `OAuthClientSecret` | (required) | Zoom OAuth app client secret |
| `EncryptionKey` | (required, auto-generated) | AES key for token encryption |
| `WebhookSecret` | (required, auto-generated) | Mattermost webhook validation secret |
| `ZoomWebhookSecret` | (required) | Zoom webhook signature verification secret |
| `RestrictMeetingCreation` | `false` | Restrict meetings to private channels only |
| `EnablePostingRecordingPassword` | `false` | Post recording password to channel |

**KV store keys**:
- `zoomtoken_<userID>`: encrypted OAuth user info
- `zoomtokenbyzoomid_<zoomID>`: lookup by Zoom ID
- `zoomSuperUserToken_`: account-level OAuth token
- `post_meeting_<meetingUUID>`: meeting-to-post mapping (24h TTL)
- `meeting_channel_<meetingID>`: meeting-to-channel subscription (24h TTL)
- `zoomuserstate_<userID>`: OAuth state during connect flow (5min TTL)

**Slash commands**: `/zoom start [topic]`, `/zoom settings`, `/zoom subscription add|remove|list <meetingID>`, `/zoom channel-settings [list]`, `/zoom help`. **User-Managed-only**: `/zoom connect`, `/zoom disconnect` (Account-Level installs are admin-authenticated; individual users do not connect).

**Network requirements**:
- Outbound HTTPS to Zoom API (`api.zoom.us` or custom `ZoomAPIURL`)
- Inbound webhooks from Zoom to `{SiteURL}/plugins/zoom/webhook`
- SiteURL required for OAuth callback redirect

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Config struct and validation | `server/configuration.go` |
| OAuth and meeting HTTP handlers | `server/http.go` |
| Webhook handling and signature verification | `server/webhook.go` |
| Slash command handlers | `server/command.go` |
| KV store operations | `server/store.go` |
| Token encryption | `server/cipher.go` |

### Common Investigation Patterns

**Account-level vs user-level OAuth**: `AccountLevelApp=true` means a single admin authenticates for everyone (matched by email). `AccountLevelApp=false` requires each user to `/zoom connect`. Mismatch between Zoom app type ("User-managed" vs "Account-level") and this setting is a common gotcha.

**Deauthorization webhook**: When users revoke the Zoom app, Zoom sends a deauthorization webhook to `{SiteURL}/plugins/zoom/webhook`. Verify Mattermost is reachable from Zoom; if missed, the user's `zoomtoken_<userID>` KV entry remains stale until they manually disconnect.

**OAuth token decrypt failure**: After `EncryptionKey` rotation, existing tokens fail. User must `/zoom disconnect` and reconnect.

**Account-Level vs User-Managed OAuth - decision tree**:

| Mattermost setting | Zoom-side label | Use when | Constraint |
|---|---|---|---|
| `AccountLevelApp=true` (UI: "OAuth by Account Level App") | **Admin-managed app** (a.k.a. Account-Level) | A single Zoom admin authenticates on behalf of the whole tenant | Only Zoom users **in the same Zoom account that created the app** can use the integration. Mattermost user's email **must match** their Zoom email exactly - identity is resolved by email + Personal Meeting ID lookup |
| `AccountLevelApp=false` (default) | **User-managed app** (a.k.a. User-Managed) | Each user OAuths individually; mixed/BYOL licensing | Each user runs `/zoom connect` independently |

Source-side enforcement: only system admins can run `/zoom connect` when `AccountLevelApp=true` (`server/command.go:137`). Mismatch between Mattermost setting and Zoom-side app type produces confusing OAuth scope or audience errors at connect time.

**Required Zoom scopes** (per admin doc, same for both modes):
- `meeting:read:meeting`, `meeting:write:meeting`, `user:read:user`, `cloud_recording:read:recording`, `archiving:read:list_archived_files`. Missing scopes -> 4xx on meeting create / recording fetch.

**Deauthorization webhook verification** (Zoom -> Mattermost when a user revokes the app):

- URL: `{SiteURL}/plugins/zoom/deauthorization` (`server/http.go:33,97`).
- Handler clears the user's `zoomtoken_<userID>` and `zoomtokenbyzoomid_<zoomID>` KV entries and DMs them: "We have received a deauthorization message from Zoom for your account..."
- Failure log signatures: `failed to dm user about deauthorization`, `failed to complete compliance after user deauthorization` (both `server/http.go:910,915`).

If the deauth DM never arrives: Mattermost is unreachable from Zoom. Verify SiteURL is publicly accessible and `/plugins/zoom/deauthorization` is not blocked by a reverse proxy. Stale `zoomtoken_<userID>` entries linger until the user manually `/zoom disconnect`s.

**Webhook test step from Zoom side** (admin doc line 65): use Zoom's "Test Event" button after configuring the webhook; expect HTTP 200. The **Secret Token** shown by Zoom must match the `WEBHOOKSECRET` in the URL query string (Zoom passes the secret as `?secret=...` rather than a header).

### Zoom Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `please configure OAuthClientID` | Missing OAuth config | Set `OAuthClientID` in plugin settings |
| `please configure OAuthClientSecret` | Missing OAuth config | Set `OAuthClientSecret` in plugin settings |
| `please generate EncryptionKey from Zoom plugin settings` | No encryption key | Generate key in System Console or set in config |
| `please configure WebhookSecret` | Missing webhook secret | Generate webhook secret in plugin settings |
| `must connect user account to Zoom first` | User not authenticated | Run `/zoom connect` to initiate OAuth flow |
| `could not decrypt OAuth access token` | Encryption key mismatch or corrupted token | User must reconnect: `/zoom disconnect` then `/zoom connect` |
| `Could not verify Mattermost webhook secret` | Invalid `WebhookSecret` in request | Verify webhook secret matches between Mattermost and caller |
| `Could not verify webhook signature` | Invalid `ZoomWebhookSecret` | Verify `ZoomWebhookSecret` matches Zoom app webhook settings |
| `Creating Zoom meeting is disabled for this channel` | `RestrictMeetingCreation` active, channel is not private | Use a private channel or disable restriction |
