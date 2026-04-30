### mattermost-plugin-msteams-meetings

**What**: Microsoft Teams Meetings audio/video conferencing integration (meetings-only). Distinct from `mattermost-plugin-msteams`, which handles channel/user sync.
**Stack**: Go backend, React frontend
**Plugin ID**: `com.mattermost.msteamsmeetings`
**Min server**: 10.7.0
**Database**: KV store only (no custom tables)

**Authentication**: OAuth 2.0 via Azure AD / Microsoft.
- Each user connects via `/mstmeetings connect`.
- OAuth tokens encrypted at rest with `EncryptionKey` (AES-256, see `server/user.go`).
- Required scopes: `offline_access`, `OnlineMeetings.ReadWrite`.

**Configuration**:

| Field | Required | Purpose |
|---|---|---|
| `OAuth2Authority` | Yes | Azure Directory (tenant) ID |
| `OAuth2ClientId` | Yes | Azure Application (client) ID |
| `OAuth2ClientSecret` | Yes | Azure client secret |
| `EncryptionKey` | Yes | AES key (auto-generated if blank) |

Plugin refuses to activate if any of the three OAuth fields is missing (`server/configuration.go`).

**KV store keys**:
- `msteamsmeetinguserstate_<userID>` - OAuth flow state (transient).
- `token_<userID>` - encrypted OAuth info + Teams identity.
- `tbyrid_<remoteID>` - reverse lookup by Teams user ID.

**Slash commands**: `/mstmeetings start [topic]`, `/mstmeetings connect`, `/mstmeetings disconnect`, `/mstmeetings help`.

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Configuration & validation | `server/configuration.go` |
| OAuth flow & HTTP handlers | `server/http.go` |
| Slash command handlers | `server/command.go` |
| User info & token encryption | `server/user.go` |
| OAuth state management | `server/state.go` |
| Meeting creation & posting | `server/post.go`, `server/meeting.go` |

### Common Investigation Patterns

**OAuth redirect mismatch**: Verify `OAuth2Authority` (tenant) and the Azure app's redirect URI. The plugin uses `{SiteURL}/plugins/com.mattermost.msteamsmeetings/oauth2/complete` as callback. Mismatch with the actual Mattermost SiteURL produces `invalid state` errors during `/mstmeetings connect`.

**Encryption key rotation**: Changing `EncryptionKey` invalidates stored tokens; the plugin auto-wipes its KV store (`server/user.go`). All connected users must re-run `/mstmeetings connect`.

**Missing user properties**: OAuth callback validates the remote user has `Mail`, `ID`, and `UserPrincipalName` (UPN). Teams/Azure users missing any of these get `User has no <field>` errors. Configure user identity in Azure AD before retrying.

### MS Teams Meetings Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `OAuthClientSecret is not configured` | Missing client secret | Set in plugin settings |
| `OAuthClientID is not configured` | Missing client ID | Set in plugin settings |
| `OAuth2Authority is not configured` | Missing tenant ID | Set Azure Directory (tenant) ID |
| `invalid state` | OAuth state mismatch / expired | Check `OAuth2Authority` and SiteURL match Azure app config; user retries `/mstmeetings connect` |
| `missing stored state` | State deleted or expired | Retry OAuth flow |
| `Not authorized, incorrect user` | User ID mismatch in OAuth callback | Verify the Mattermost session matches |
| `error getting token` | Azure OAuth exchange failed | Check client-secret validity; verify tenant/app IDs |
| `User has no mail` / `... ID` / `... user principal name` | Missing Azure AD attribute | Configure user identity in Azure |
| `unable to decrypt user OAuth2 token` | Encryption key changed or corrupted | User runs `/mstmeetings disconnect` then `/mstmeetings connect` |
| `Your Mattermost account is not connected to any Microsoft Teams account` | No stored token | Run `/mstmeetings connect` first |
