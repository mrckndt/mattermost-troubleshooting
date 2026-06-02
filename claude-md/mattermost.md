### mattermost (server + webapp)

#### Reverse proxy in front of Mattermost

Mattermost's built-in HTTP server can serve clients directly, but Mattermost recommends running a reverse proxy (NGINX is the documented reference) in front of it for production:

- **Connection and session handling:** NGINX better handles large numbers of concurrent connections, keep-alives, and slow/intermittent clients, freeing the Mattermost process from holding those resources.
- **TLS termination:** offload certificate handling, cipher selection, OCSP stapling, and TLS 1.2/1.3 negotiation to NGINX instead of Mattermost's less flexible built-in TLS.

**Reference:** `https://docs.mattermost.com/deployment-guide/server/setup-nginx-proxy.html`.

#### Server fails to bind: `listen tcp :443: bind: permission denied`

**Cause:** on Linux, binding to ports below 1024 requires `CAP_NET_BIND_SERVICE`, which the `mattermost` user lacks by default, causing `ServiceSettings.ListenAddress = ":443"` (or `:80`) to fail at startup.

**Fix:** terminate TLS in a reverse proxy (see above) and keep Mattermost on its default `:8065`. If Mattermost must bind `:443` / `:80` directly, grant the capability to the binary:

```
sudo setcap 'cap_net_bind_service=+ep' /opt/mattermost/bin/mattermost
```

Re-apply after every upgrade; package upgrades replace the binary and drop the capability. Do not run Mattermost as `root` to work around this.

#### Database connection pool sizing

- Keep `SqlSettings.MaxOpenConns` and `MaxIdleConns` at a 2:1 ratio (e.g. 100 and 50).
- `MaxOpenConns` must not exceed the database's `max_connections` limit.
- In a cluster, each node opens its own pool and the database must accommodate their sum. For a 3-node cluster with `MaxOpenConns=100` per node, PostgreSQL needs `max_connections >= 300` plus headroom for superuser, replication, and other clients.
- **Pool-exhaustion signature:** `context deadline exceeded` on store calls. Two causes: (a) `MaxOpenConns` exceeds the database's `max_connections` (e.g. 300 vs. PostgreSQL default 100), saturating the pool; or (b) `MaxOpenConns` is too low for the workload. Fix (a): raise `max_connections` to the sum of `MaxOpenConns` across all nodes plus headroom. Fix (b): raise `MaxOpenConns` accordingly.
- **Query-timeout signature:** when `SqlSettings.QueryTimeout` is exceeded, the `pq` driver logs `pq: canceling statement due to user request`. Distinct from pool exhaustion above.

#### Cluster gossip: `model.ClusterMessage.LogFields()`

`LogFields()` was added to `model.ClusterMessage` in v11.7.0 (PR #36214). It partially unmarshals message `Data` on error paths only (no performance impact on normal traffic) to surface `ws_event`, `channel_id`, `team_id`, `omit_users_len` for publish events, and `plugin_id`/`event_id` for plugin events. For troubleshooting `sendto: message too long` errors, see "Cluster gossip drop" in the enterprise notes.

#### MariaDB is not a supported backend

MariaDB is **not** supported. It diverges from MySQL enough that queries can fail in different places as the codebase evolves. The fix is always the same: migrate to MySQL 8.0 or PostgreSQL. Don't tune around individual symptoms.

**Symptom** (v10.5+, mobile push delivery): notifications log entries like

```
Failed to send mobile app sessions ... fetch_error ... Error 1064 (42000): You have an error in your SQL syntax;
check the manual that corresponds to your MariaDB server version for the right syntax to use near
''$.last_removed_device_id', '')' at line 1
```

**Cause:** MariaDB's JSON function syntax differs from MySQL's, breaking the Sessions query for `Props.last_removed_device_id` and preventing notifications from delivering. Other JSON-heavy or MySQL-only features will break similarly. **Migration reference:** `https://blogs.oracle.com/mysql/post/how-to-migrate-from-mariadb-to-mysql-80`.
