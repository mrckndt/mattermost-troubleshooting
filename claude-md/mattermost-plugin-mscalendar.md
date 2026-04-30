### mattermost-plugin-mscalendar

**What**: Microsoft Outlook / Office 365 calendar integration - event reminders, status sync from calendar busy slots, meeting responses
**Stack**: Go backend, React frontend
**Plugin ID**: `com.mattermost.mscalendar`
**Min server**: 10.7.0
**Database**: KV store via plugin API (no custom SQL tables); user data encrypted at rest

**Authentication**: OAuth 2.0 via Microsoft Graph. Requires Azure AD app registration with tenant ID, client ID, and client secret.

**Configuration** (System Console -> Plugins -> Microsoft Calendar):

| Field | Purpose |
|---|---|
| `OAuth2Authority` | Azure Directory (tenant) ID |
| `OAuth2ClientId` | Azure Application (client) ID |
| `OAuth2ClientSecret` | Azure client secret |
| `OAuth2ForceConsent` | Force consent prompt; set `false` if Azure requires admin consent for non-admin users |
| `AdminUserIDs` | Plugin admins beyond System Admins |
| `AdminLogLevel` | Admin DM log level (none / debug / info / warn / error) |

**Slash commands**: `/mscalendar connect`, `/mscalendar disconnect`, `/mscalendar summary [view|today|tomorrow|settings|time|enable|disable]`, `/mscalendar viewcal`, `/mscalendar settings`, `/mscalendar today`, `/mscalendar tomorrow`, `/mscalendar info`, `/mscalendar help`.

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| OAuth handling | `calendar/engine/oauth2.go` |
| Status sync / availability | `calendar/engine/availability.go` |
| Event notifications | `calendar/engine/notification.go`, `calendar/api/notification.go` |
| Daily summary | `calendar/engine/daily_summary.go` |
| Webhook subscriptions | `calendar/engine/subscription.go` |
| Slash command handlers | `calendar/command/command.go` |
| KV store layer | `calendar/utils/kvstore/kvstore.go` |

### Common Investigation Patterns

**Missed reminders**: Verify the user's webhook subscription is active. Subscriptions expire ~3 days and must be renewed by `RenewMyEventSubscription` (`calendar/engine/subscription.go`). Inspect the user's KV settings for an `EventSubscriptionID`. Event-notification trigger window is 10 minutes (see `availability.go`).

**Status not updating from calendar**: Status sync runs every 5 minutes (`availability.go`). Confirm the user is connected and that calendar events mark them as "busy" - sync queries busy slots in a 10-minute window. Timezone mismatch produces wrong-time syncs; verify mailbox timezone via `GetMailboxSettings` (in `oauth2.go`).

**OAuth token expiry / reconnection required**: Tokens are auto-refreshed via `oauth2.Exchange`. After a password change or long inactivity, the refresh token can be invalidated; the user must `/mscalendar disconnect` then `/mscalendar connect`. The Azure app registration must have `offline_access` scope to issue refresh tokens.
