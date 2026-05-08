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

**Shared engine with `mattermost-plugin-mscalendar`**: this plugin imports `github.com/mattermost/mattermost-plugin-mscalendar/calendar/{engine,jobs,plugin,remote}` (`server/main.go:9-11`). The same daily renewal cron and notification framework apply. The `gcal/` package is just the Google-specific client.

**Subscription TTL and renewal**:
- Google watch channel: 7-day TTL (`subscribeTTL = 7 * 24 * time.Hour`, `gcal/subscription.go:19`).
- Renewal cron: 24 h interval (inherited from mscalendar engine - same `id: "renew"` job).
- Renewal mechanism: `RenewSubscription` deletes the old channel and creates a new one; see `gcal/subscription.go:94-106`.
- Failure logs: `gcal CreateMySubscription, error creating subscription` (`subscription.go:47`); `gcal RenewSubscription, error deleting subscription` (`subscription.go:98,103`).

**Bare-notification handling** (`gcal/webhook.go:30-58`): Google delivers only headers (`X-Goog-Resource-State`, `X-Goog-Channel-Id`, etc.) - no event body. The handler builds a bare notification and the engine then calls `GetNotificationData()` to fetch the actual event from the Calendar API. If this second call fails (token expired, scope missing, network), the user gets no reminder. Initial subscription handshake: Google sends `X-Goog-Resource-State: sync` once on channel creation - returns 202 with no notifications, normal behaviour.

If reminders stop arriving for one user only, check logs for `error fetching event data` from `GetNotificationData`. Token refresh + scope re-grant usually resolves it.

### Google Calendar Plugin Errors

| Message | Cause | Resolution |
|---|---|---|
| `OAuth2 credentials to be set in the config` | Missing `OAuth2ClientID` or `OAuth2ClientSecret` | Set in plugin settings |
| `encryption key cannot be empty` | `EncryptionKey` not generated | Generate in plugin settings |
| `Not able to refresh or store the token for user` | Refresh token expired / revoked | User runs `/gcal disconnect` then `/gcal connect` |
| `gcal CreateMySubscription, error creating subscription` | Calendar API service creation failed | Verify scopes; check Google API quota |
| `gcal DeleteSubscription, error from google response` | Watch-channel unsubscribe failed | Check Google Calendar API status; retry |
