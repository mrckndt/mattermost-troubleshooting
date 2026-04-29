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

**Config struct groups** (46 groups in `server/public/model/config.go`): ServiceSettings, SqlSettings, LogSettings, FileSettings, EmailSettings, LdapSettings, SamlSettings, ClusterSettings, PluginSettings, ElasticsearchSettings, DataRetentionSettings, and 35 others. See source for full list.

**Database**: PostgreSQL (primary, recommended) and MySQL. Default connection pool: `MaxIdleConns=50`, `MaxOpenConns=100`, `ConnMaxLifetimeMilliseconds=3600000` (1h), `ConnMaxIdleTimeMilliseconds=300000` (5m), `QueryTimeout=30` (seconds). Read replicas supported via `DataSourceReplicas`.
