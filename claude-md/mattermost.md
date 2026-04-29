### mattermost (server + webapp)

**What**: Core Mattermost platform - Go backend with React web frontend
**Stack**: Go (server), React/TypeScript (webapp), PostgreSQL/MySQL
**Architecture layers**: `model` -> `sqlstore` -> `app` -> `api4` / `wsapi` -> `web`
**Store chain**: sqlstore -> localcachelayer -> searchlayer -> retrylayer -> timerlayer

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| All config structs and defaults | `server/public/model/config.go` |
| Config validation (SetDefaults, IsValid) | `server/public/model/config.go` |
| REST API v4 handlers (157 files) | `server/channels/api4/` |
| WebSocket handlers | `server/channels/wsapi/` |
| Business logic | `server/channels/app/` |
| SQL queries and store layer | `server/channels/store/sqlstore/` |
| Plugin infrastructure | `server/channels/app/plugin*.go` |
| Plugin API interface (100+ hooks) | `server/public/plugin/api.go`, `server/public/plugin/hooks.go` |
| Authentication logic | `server/channels/app/authentication.go`, `server/channels/app/login.go` |
| LDAP (enterprise) | `server/enterprise/ldap/` |
| SAML (enterprise) | `server/enterprise/saml/` |
| Push notifications | `server/channels/app/notification_push.go` |
| Logging setup | `server/channels/app/server.go` |
| Config file resolution | `server/config/file.go` |
| Environment variable overrides | `server/config/environment.go` |
| Database migrations | `server/channels/db/migrations/` |
| Background jobs (36 registered types) | `server/channels/jobs/` |

To list config struct groups, grep `^type \w+Settings struct` in `server/public/model/config.go`. The Config struct itself is in the same file.

**Database**: PostgreSQL (primary, recommended) and MySQL. Default connection pool: `MaxIdleConns=50`, `MaxOpenConns=100`, `ConnMaxLifetimeMilliseconds=3600000` (1h), `ConnMaxIdleTimeMilliseconds=300000` (5m), `QueryTimeout=30` (seconds), `AnalyticsQueryTimeout=300s`. Read replicas supported via `DataSourceReplicas`; search-specific replicas via `DataSourceSearchReplicas`. Defaults defined in `server/public/model/config.go` (`SqlSettings.SetDefaults()`); to verify in a given release, grep `MaxIdleConns =` in that file.

### Database support matrix (all components)

| Component | PostgreSQL | MySQL | Notes |
|---|---|---|---|
| Mattermost Server | Yes (primary) | Yes | PostgreSQL recommended |
| Plugin: Calls | Yes | Yes | Custom tables: `calls_*` |
| Plugin: Playbooks | Yes | **No** | Hard requirement; errors on MySQL |
| Plugin: Boards | Yes | Yes | See `mattermost-plugin-boards.md` |
| Plugin: Agents | Yes (pgvector for search) | Partial | pgvector extension required for semantic search |
| Plugin: Jira | N/A | N/A | Uses KV store, no direct SQL |
| Plugin: Zoom | N/A | N/A | Uses KV store, no direct SQL |
| Plugin: GitHub | N/A | N/A | Uses KV store, no direct SQL |
| Plugin: GitLab | N/A | N/A | Uses KV store, no direct SQL |

### Key tables by component

**Server core** (partial list): `Users`, `Channels`, `Posts`, `Teams`, `Sessions`, `Tokens`, `OAuthApps`, `OAuthAccessData`, `Preferences`, `Status`, `FileInfo`, `Reactions`, `ChannelMembers`, `TeamMembers`, `Commands`, `IncomingWebhooks`, `OutgoingWebhooks`, `PluginKeyValueStore`.

**Calls**: `calls_channels` (channel call settings), `calls` (active/past calls), `calls_sessions` (user sessions in calls), `calls_jobs` (recording/transcription jobs).

**Playbooks** (all `IR_` prefixed): `IR_Incident` (playbook runs), `IR_Playbook` (templates), `IR_PlaybookMember`, `IR_StatusPosts`, `IR_TimelineEvent`, `IR_UserInfo`, `IR_ViewedChannel`.

### Architecture deep-dives

These are non-obvious behaviors and tribal knowledge that aren't easily inferred from skim-reading the code. Cite the exact file path so they can be re-validated.

**Session / token resolution chain** (`server/channels/app/authentication.go` `ParseAuthTokenFromRequest()` and `server/channels/app/session.go` `GetSession()`):

1. Token extraction priority (incoming request): session cookie `MMAUTHTOKEN` -> `Authorization: Bearer <token>` -> `Authorization: Token <token>` (OAuth) -> `access_token` query param -> Cloud token header (separate path: `GetCloudSession()`) -> Remote cluster token header (separate path: `GetRemoteClusterSession()`).
2. `GetSession()` first checks the session cache/DB via `platform.GetSession()`.
3. If not found, it falls through to `createSessionForUserAccessToken()` which looks up the token in the `UserAccessTokens` table.
4. If that also fails, the warning logged mentions "user access token" - **misleading**: any token type (session cookie, OAuth, WebSocket reconnect) lands here on miss.
5. All token formats look identical (`model.NewId()`, 26-char alphanumeric). You cannot distinguish session vs personal-access vs OAuth tokens by format alone.
6. WebSocket reconnects after a server restart hit this same path en masse, producing burst log noise (`server/channels/app/platform/websocket_router.go` "Error while getting session token" companion log lines). Harmless; clients re-authenticate after 401.

**`UpdatePost` does NOT trigger `SendNotifications`** (`server/channels/app/post.go`):

- `CreatePost` calls `handlePostEvents()` -> `SendNotifications()` (`server/channels/app/notification.go`): full email/push/desktop notification pipeline.
- `UpdatePost` only broadcasts `WebsocketEventPostEdited` for live UI refresh. No email/push/desktop notifications on edits.
- Plugin hooks (in `server/public/plugin/hooks.go`): `MessageHasBeenPosted` (after CreatePost), `MessageWillBeUpdated` / `MessageHasBeenUpdated` (around UpdatePost). Neither edit hook reaches `SendNotifications`.
- Workaround: a bot can post a reply (`CreatePost` with `root_id`) instead of editing - replies trigger notifications to thread followers.

**Bot exemptions in domain checks** (`server/channels/app/teams/utils.go`):

- `IsTeamEmailAllowed()` exempts bots (first check: `user.IsBot == true`). Used by `JoinUserToTeam` and `CreateTeamWithUser`.
- BUT `CreateUserWithInviteId` in `user.go` calls `CheckUserDomain()` directly - **no bot exemption**. Both error IDs (`api.team.join_user_to_team.allowed_domains.app_error`, `api.team.is_team_creation_allowed.domain.app_error`) produce the same user-facing message.
- Guests: checked against `GuestAccountsSettings.RestrictCreationToDomains` instead of the team's `AllowedDomains`.

**License-checking pattern**: enterprise features gate themselves with a nil-check on `c.App.Channels().License()` followed by a dereference of the relevant `Features.<Name>` flag (or a tier-min helper). On gate failure, an `AppError` is returned. Grep for `License().Features.` to find every gate. License model: `server/public/model/license.go`. SKUs: E10, E20, Professional, Enterprise, Enterprise Advanced, Mattermost Entry. Plugin-side helpers (`server/public/pluginapi/license.go`): `IsEnterpriseLicensedOrDevelopment()`, `IsE10/E20LicensedOrDevelopment()`.

**Cloud / CWS gate** (`server/channels/api4/cloud.go`):

- `ensureCloudInterface()` checks two things before delegating to enterprise: cloud interface registered (enterprise compiled in) AND `CloudSettings.Disable != true`.
- `MM_CLOUDSETTINGS_DISABLE=true` disables all CWS interactions.
- Enterprise impl: `CheckCWSConnection` in `server/einterfaces/cloud.go`.

### Tools

**Build mmctl**:
```
cd upstream/mattermost/server && make mmctl-build
```

Cross-compile example:
```
cd upstream/mattermost/server && GOOS=linux GOARCH=amd64 go build -trimpath -o bin/mmctl-linux-amd64 ./cmd/mmctl
```

mmctl entry: `server/cmd/mmctl/`. Commands under `commands/` (~46 files). Local mode (`--local`) connects via Unix socket and bypasses auth; remote mode uses token-based API.

### Common Support Investigation Patterns

**"Where is config setting X validated?"**
1. Find the field name in `server/public/model/config.go`.
2. The parent struct's `isValid()` method in the same file holds the validation.
3. `SetDefaults()` shows the default.

**"What does API endpoint W do?"**
1. Identify the resource (users, channels, teams, etc.).
2. Open `server/channels/api4/<resource>.go`; the `Init<Resource>()` function registers routes.
3. Follow the handler to business logic in `server/channels/app/`.

**"Why are there 'user access token' warnings in the logs?"**
1. Coincides with a server restart? Search the same log for "Starting Server" or "Current version".
2. Look for the companion `websocket_router.go` "Error while getting session token" lines - confirms WebSocket reconnection storm.
3. Same token repeating on a schedule (e.g. every 5 min) is an integration with a stale token.
4. Burst of distinct tokens after restart is the normal reconnection storm - harmless.

**"Why didn't editing a post send notifications?"**
1. `UpdatePost` does NOT call `SendNotifications` - only `CreatePost` does.
2. Workaround: bot posts a reply with `root_id` set (triggers thread-follower notifications).

**"Can a bot join a team that has domain restrictions?"**
1. `IsTeamEmailAllowed()` exempts bots. So `JoinUserToTeam` works.
2. BUT `CreateUserWithInviteId` calls `CheckUserDomain()` directly with no bot exemption. So the invite-link path will reject the bot.
3. Confirm the account is actually a bot (`is_bot: true`) vs a regular account used like one.

**"Is feature Z enterprise-only?"**
1. Check `server/public/model/license.go` Features struct.
2. Grep for `License().Features.<Name>` to find gates.
3. Interface (if applicable) in `server/einterfaces/`; implementation in `upstream/enterprise/<feature>/`.

**"What does mmctl command V do?"**
1. `server/cmd/mmctl/commands/<resource>.go`.
2. Cobra command definition for usage/description.
3. The `RunE` function for implementation.
