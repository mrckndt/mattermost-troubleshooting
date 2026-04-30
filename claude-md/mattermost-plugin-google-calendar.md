### mattermost-plugin-google-calendar

**What**: Google Calendar integration - event management, availability sync, event reminders
**Stack**: Go backend (`gcal/` package), React frontend
**Plugin ID**: `com.mattermost.gcal`
**Min server**: 10.7.0
**Database**: KV store, encrypted with `EncryptionKey` (AES)

**Authentication**: OAuth 2.0 with Google.
- User-initiated: `/gcal connect`.
- Scopes: `calendar.CalendarScope`, `calendar.CalendarSettingsReadonlyScope`, `people.UserinfoEmailScope`, `people.UserinfoProfileScope` (`gcal/remote.go`).
- Token refresh: tokens auto-refreshed before expiration; encrypted in KV store.

**Configuration** (from `plugin.json`):

| Field | Type | Purpose |
|---|---|---|
| `OAuth2ClientID` | text | Google OAuth Client ID (required) |
| `OAuth2ClientSecret` | text | Google OAuth Client Secret (required) |
| `EncryptionKey` | generated | AES key for token storage (required, auto-generated) |
| `AdminUserIDs` | text | Comma-separated admin user IDs |
| `AdminLogLevel` | dropdown | Log level for admin DMs (none / debug / info / warn / error) |
| `AdminLogVerbose` | bool | Full context in admin log messages |

**Slash commands**: `/gcal connect`, `/gcal disconnect`, `/gcal today`, `/gcal tomorrow`, `/gcal viewcal`, `/gcal settings`, `/gcal event create`.

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Google OAuth config & scopes | `gcal/remote.go` |
| Webhook ingestion (watch channel) | `gcal/webhook.go` |
| Subscription (watch) lifecycle | `gcal/subscription.go` |
| Event creation / listing | `gcal/event.go` |
| Notification fetching from webhook | `gcal/notifications.go` |
| HTTP client / Google API calls | `gcal/client.go` |

### Common Investigation Patterns

**OAuth scope / token refresh failures**: Missing or insufficient scopes (calendar, people APIs) cause auth errors. Check `NewOAuth2Config()` in `gcal/remote.go`. Token-refresh failures log as `Not able to refresh or store the token`; user must `/gcal disconnect` then reconnect.

**Webhook subscription expiry**: Watch-channel subscriptions expire after 7 days (`gcal/subscription.go`). Missing renewals cause missed event updates. Inspect subscription TTL and renewal cron logs; the webhook URL `{SiteURL}/plugins/gcal/webhook` must be reachable from Google.

**Bare webhook notifications**: Google may deliver "bare" notifications without full event data. The plugin then calls `GetNotificationData()` to fetch event details from the Calendar API (`gcal/notifications.go`). Network or auth failures here block notification delivery.

### Google Calendar Plugin Errors

| Message | Cause | Resolution |
|---|---|---|
| `OAuth2 credentials to be set in the config` | Missing `OAuth2ClientID` or `OAuth2ClientSecret` | Set in plugin settings |
| `encryption key cannot be empty` | `EncryptionKey` not generated | Generate in plugin settings |
| `Not able to refresh or store the token for user` | Refresh token expired / revoked | User runs `/gcal disconnect` then `/gcal connect` |
| `gcal CreateMySubscription, error creating subscription` | Calendar API service creation failed | Verify scopes; check Google API quota |
| `gcal DeleteSubscription, error from google response` | Watch-channel unsubscribe failed | Check Google Calendar API status; retry |
