### mattermost-plugin-playbooks

**What**: Incident response and workflow automation plugin
**Stack**: Go backend, React frontend
**Plugin ID**: `playbooks`
**Min server**: 11.1.0
**Database**: **PostgreSQL ONLY** (explicitly rejects MySQL)
**License**: Requires Professional or higher

**Configuration** (from `server/config/configuration.go`):
- `BotUserID`: system bot for posting messages
- `EnableTeamsTabApp`: Microsoft Teams Tab integration (default: false)
- `TeamsTabAppTenantIDs`: comma-separated Azure AD tenant IDs
- `EnableIncrementalUpdates`: WebSocket optimization (default: false)
- `EnableExperimentalFeatures`: beta features (default: false)

**Database tables** (all prefixed `IR_`): `IR_Incident` (playbook runs), `IR_Playbook` (templates), `IR_PlaybookMember`, `IR_StatusPosts`, `IR_TimelineEvent`, `IR_UserInfo`, `IR_ViewedChannel`
Migrations: 164 (PostgreSQL only) at `server/sqlstore/migrations/postgres/`

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Plugin entry point | `server/plugin.go` |
| Configuration | `server/config/configuration.go` |
| SQL store and migrations | `server/sqlstore/` |
| Error definitions | `server/app/errors.go` |
| Playbook run service | `server/app/playbook_run_service.go` |

### Common Investigation Patterns

**MySQL not supported**: Plugin activation fails with `unsupported database type X for migration`. Playbooks is PostgreSQL-only; the customer must migrate. Point to `deployment-guide/postgres-migration.rst` in the docs repo.

**Run not starting**: License gate (`OnActivate` license-check failure) - confirm Professional or higher. Otherwise, look in `server/app/playbook_run_service.go` for run-creation errors; common causes are missing playbook ID or insufficient channel permissions for the requested channel mode.

**Status update missing**: Status updates are scheduled posts. If they don't appear, check the run isn't already finished (`ErrPlaybookRunNotActive`); inspect `IR_StatusPosts` for the expected entry. WebSocket update events use `EnableIncrementalUpdates` (default false).

**Retrospective permissions denied**: Retros are channel-scoped. Confirm the user is a run participant or playbook member; check `IR_PlaybookMember` for the role.

### Playbooks Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `unsupported database type X for migration` | Running on MySQL | Playbooks requires PostgreSQL; migrate database |
| `ErrPlaybookRunNotActive` | Action attempted on completed run | Verify run status before operating on it |
| `ErrPlaybookRunActive` | Action requires run to be finished | End the run first |
| `ErrDuplicateEntry` | Duplicate record in database | Check for conflicting data |
| License check failure on `OnActivate` | No Professional/Enterprise license | Playbooks requires Professional license or higher |
