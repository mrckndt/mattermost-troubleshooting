### mattermost (server + webapp)

#### Reverse proxy in front of Mattermost

Mattermost's built-in HTTP server can serve clients directly, but Mattermost recommends running a reverse proxy (NGINX is
the documented reference) in front of it for production:

- **Connection and session handling:** NGINX better handles large numbers of concurrent connections, keep-alives, and
  slow/intermittent clients, freeing the Mattermost process from holding those resources.
- **TLS termination:** NGINX takes over certificate handling, cipher selection, OCSP stapling, and TLS 1.2/1.3
  negotiation from Mattermost's less flexible built-in TLS.

**Reference:** `https://docs.mattermost.com/deployment-guide/server/setup-nginx-proxy.html`.

#### Server fails to bind: `listen tcp :443: bind: permission denied`

**Cause:** on Linux, binding to ports below 1024 requires `CAP_NET_BIND_SERVICE`. The `mattermost` user lacks it by
default, so `ServiceSettings.ListenAddress = ":443"` (or `:80`) fails at startup.

**Fix:** terminate TLS in a reverse proxy (see above) and keep Mattermost on its default `:8065`. If Mattermost must bind
`:443` / `:80` directly, grant the capability to the binary:

```
sudo setcap 'cap_net_bind_service=+ep' /opt/mattermost/bin/mattermost
```

Re-apply after every upgrade; package upgrades replace the binary and drop the capability. Do not run Mattermost as
`root` to work around this.

#### Database connection pool sizing

- **Ratio:** keep `SqlSettings.MaxOpenConns` and `MaxIdleConns` at 2:1 (e.g. 100 and 50).
- **Per pool:** `MaxOpenConns` sizes one pool, not a total. Each node opens a separate pool for the master, each
  `DataSourceReplicas` entry, and each `DataSourceSearchReplicas` entry.
- **Sizing:** possible connections = `MaxOpenConns` x (data sources per node) x (app nodes). Example: 3 nodes, master +
  1 replica + 1 search replica, `MaxOpenConns=100`: 3 x 3 x 100 = 900.

**Pool-exhaustion signature:** `context deadline exceeded` on store calls. Two causes:

- **Pool oversubscribed:** `MaxOpenConns` exceeds the database's `max_connections` (e.g. 300 vs. the PostgreSQL default
  100), saturating the pool. Fix: raise `max_connections` accordingly, plus headroom for superuser, replication, and
  other clients.
- **Pool too small:** `MaxOpenConns` is too low for the workload. Fix: raise `MaxOpenConns` accordingly.

**Query-timeout signature:** when `SqlSettings.QueryTimeout` is exceeded, the `pq` driver logs
`pq: canceling statement due to user request`. Distinct from pool exhaustion.

#### MariaDB is not a supported backend

MariaDB is not supported. It diverges from MySQL enough that queries can fail in different places as the codebase
evolves. The fix is always the same: migrate to MySQL 8.0 or PostgreSQL rather than tuning around individual symptoms.

**Symptom (v10.5+, mobile push delivery):** notifications log entries like

```
Failed to send mobile app sessions ... fetch_error ... Error 1064 (42000): You have an error in your SQL syntax;
check the manual that corresponds to your MariaDB server version for the right syntax to use near
''$.last_removed_device_id', '')' at line 1
```

**Cause:** MariaDB's JSON function syntax differs from MySQL's, breaking the Sessions query for
`Props.last_removed_device_id` and preventing notifications from delivering. Other JSON-heavy or MySQL-only features
break similarly.

**Migration reference:** `https://blogs.oracle.com/mysql/post/how-to-migrate-from-mariadb-to-mysql-80`.

#### Pin/unpin blocked by PostEditTimeLimit (v11.7.0+)

**Symptom:** users cannot pin/unpin a post older than `ServiceSettings.PostEditTimeLimit` (e.g. 172800 = 2 days); newer
posts pin fine. Debug log on `/pin` or `/unpin`:

```
"msg":"Post edit is only allowed for 172800 seconds...","err_where":"saveIsPinnedPost","path":"/api/v4/posts/<id>/pin","http_code":400
```

**Cause:** v11.7.0 (PR #35638, commit `a19cc4b909`) extended the edit time limit from message text to any post mutation,
including `IsPinned`:

- `saveIsPinnedPost` now calls `postEditTimeLimitExpired` (`server/channels/api4/post.go:1349`); before 11.7.0 the
  pin/unpin endpoints had no time-limit check. Still present on `master`.
- Re-pinning an already-pinned post is exempt (`post.go:1343`).

**Not permissions/license:** the failure is the time-limit `AppError` (HTTP 400), not a 403. The pin path checks only
read-channel permission plus the time limit; it ignores `AllowEditPost`/`edit_post`, so changing edit permissions has no
effect.

**Fix:** raise `ServiceSettings.PostEditTimeLimit` in `config.json` to a window that covers expected pinning, or set `-1`
for unlimited. The setting is `config.json`-only (System Console control deprecated) and read live via the config
watcher; no restart.

**Tradeoff:** the same setting governs message editing, so raising it also widens the edit window.

#### `upstream/docs` is a full monorepo clone pinned to `master`

Docs now live in-tree at `docs/main`/`docs/develop`. `v11.10` is the first release with `docs/` present; older tags have
none. Never `/git-switch docs` off `master`. Once every supported version is `>= v11.10`, retire this clone and read
docs from the version-aligned `upstream/mattermost` instead.
