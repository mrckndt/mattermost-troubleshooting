### mattermost-plugin-boards

**What**: Project management plugin (Trello/Notion-style boards)
**Stack**: Go backend, React frontend
**Plugin ID**: `focalboard`
**Min server**: 10.7.0
**Database**: PostgreSQL and MySQL (81 migrations)

**Config**: `EnablePublicSharedBoards` (bool, default false), data retention settings inherited from server.

**Key paths**: `server/services/store/sqlstore/migrations/` (migrations), `server/model/error.go` (error types)
