### mattermost-plugin-zoom

**What**: Zoom audio and video conferencing integration for Mattermost
**Stack**: Go backend, React frontend
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

**Slash commands**: `/zoom start [topic]`, `/zoom connect`, `/zoom disconnect`, `/zoom settings`, `/zoom subscription add|remove|list <meetingID>`, `/zoom channel-settings [list]`, `/zoom help`

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
