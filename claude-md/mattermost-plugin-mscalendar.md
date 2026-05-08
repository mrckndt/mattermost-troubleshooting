### mattermost-plugin-mscalendar

**What**: Microsoft Outlook / Office 365 calendar integration - event reminders, status sync from calendar busy slots, meeting responses
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

Azure AD app setup (admin consent, redirect URI, scopes per plugin) - see the shared `CLAUDE.md > Azure AD app registration (for Microsoft-stack plugins)` section. Authoritative admin doc: `upstream/docs/source/integrations-guide/microsoft-calendar.rst`.

**Plugin pre-packaged with Mattermost v9.11.2+** (ESR) and Cloud v10+: the plugin ships in-server. Manual upload on those versions causes version skew. Check `mmctl plugin list` for duplicates.

**Subscription renewal cron** (every connected user's event subscription, every 24 h):

- Job: `id: "renew"`, `interval: 24 * time.Hour` (`calendar/jobs/renew_job.go:12-17`).
- Iterates connected users with a 50ms dither (`ditherRenew`).
- Calls `RenewMyEventSubscription()` per user (`calendar/engine/subscription.go:76`).
- Failure log: `Error renewing subscription. err=<...>` (Error level, `renew_job.go:37`).
- Expired-sub recovery (creates new instead of renewing): `Subscription <id> for Mattermost user <id> has expired. Creating a new subscription now.` (Info level, `subscription.go:100`).

If reminders stop arriving cluster-wide for everyone at once, the renewal job is failing - grep `Error renewing subscription`. If only one user is affected, that user's stored `EventSubscriptionID` is stale - `/mscalendar disconnect` then `/mscalendar connect` re-creates it.
