### mattermost-plugin-boards

**What**: Project management plugin (Trello/Notion-style boards)
**Plugin ID**: `focalboard`
**Min server**: 10.7.0
**Database**: PostgreSQL and MySQL (81 migrations)

**Config**: `EnablePublicSharedBoards` (bool, default false). Data retention settings inherited from server.

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Plugin entry point | `mattermost-plugin/server/boards.go` |
| Server services and store layer | `server/services/store/` |
| SQL migrations (PostgreSQL & MySQL) | `server/services/store/sqlstore/migrations/` |
| Error types | `server/model/error.go` |
| API handlers | `server/api/` |
| Block / board models | `server/model/` |

### Common Investigation Patterns

**Plugin uploaded but migrations fail mid-way**: Inspect the `focalboard_schema_migrations` table for the failing version. Boards uses the same morph-based migration system as the OSS server but in its own schema. Failures usually trace to leftover state from a partial previous install; rolling back the failed migration manually + retrying is sometimes the only path.

**Public shared boards not loading**: Two-layer check: `EnablePublicSharedBoards=true` in plugin config AND `ServiceSettings.EnablePublicLink=true` on the server. The board itself must also be marked shareable.

**No new releases / customer asks about future support**: Project is discontinued. Recommend exporting via the boards UI and migrating to alternative tooling.
