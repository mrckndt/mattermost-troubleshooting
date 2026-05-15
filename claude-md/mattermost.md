### mattermost (server + webapp)

#### Reverse proxy in front of Mattermost

Mattermost's built-in HTTP server can serve clients directly, but Mattermost recommends running a reverse proxy (NGINX is the documented reference) in front of it for production:

- **Connection and session handling:** NGINX is more optimized for handling large numbers of concurrent client connections, keep-alives, and buffering of slow/intermittent clients than the Go `net/http` server, freeing the Mattermost process from holding those resources.
- **TLS termination:** offload certificate handling, cipher selection, OCSP stapling, and TLS 1.2/1.3 negotiation to NGINX. Mattermost's built-in TLS works but is less flexible.

Reference: `https://docs.mattermost.com/deployment-guide/server/setup-nginx-proxy.html`.

#### Server fails to bind: `listen tcp :443: bind: permission denied`

Cause: on Linux, binding to ports below 1024 requires `CAP_NET_BIND_SERVICE`. The `mattermost` user (under which `mattermost.service` runs) doesn't have it by default, so `ServiceSettings.ListenAddress = ":443"` (or `:80`) fails at startup.

Preferred fix: terminate TLS in a reverse proxy (see above) and keep Mattermost on its default `:8065`. If Mattermost must bind `:443` / `:80` directly, grant the capability to the binary:

```
sudo setcap 'cap_net_bind_service=+ep' /opt/mattermost/bin/mattermost
```

Re-apply after every upgrade; package upgrades replace the binary and drop the capability. Do not run Mattermost as `root` to work around this.

#### Database connection pool sizing

- `SqlSettings.MaxOpenConns` and `SqlSettings.MaxIdleConns` should be kept at a 2:1 ratio (e.g. `MaxOpenConns=100`, `MaxIdleConns=50`).
- `MaxOpenConns` must not exceed the database's connection limit (PostgreSQL `max_connections`, MySQL `max_connections`).
- In a Mattermost cluster, each node opens its own pool. The database must accommodate the sum across all nodes: for a 3-node cluster with `MaxOpenConns=100` per node, PostgreSQL needs `max_connections >= 300` (plus headroom for superuser, replication, and other clients).
- Pool-exhaustion signature: `context deadline exceeded` on store calls. Happens whenever callers wait too long for a free connection, which has two common causes: (a) `MaxOpenConns` exceeds the database's connection limit (e.g. `MaxOpenConns=300` against PostgreSQL default `max_connections=100`), so the pool silently saturates at the DB ceiling; or (b) `MaxOpenConns` is simply too low for the workload and the pool saturates on its own. Fix (a): raise PostgreSQL `max_connections` to at least the sum of `MaxOpenConns` across cluster nodes, plus headroom. Fix (b): raise `MaxOpenConns` (and `max_connections` accordingly).
- Query-timeout signature: when `SqlSettings.QueryTimeout` is exceeded, the `pq` driver cancels the in-flight query and logs `pq: canceling statement due to user request`. Distinct from the pool-exhaustion path above.

#### MariaDB is not a supported backend

MariaDB is **not** a supported database backend. It diverges from MySQL enough that Mattermost queries can fail in different places as the codebase evolves. The fix is always the same: migrate to MySQL 8.0 (or PostgreSQL). Don't tune around individual symptoms.

Observed signature (v10.5+, mobile push delivery): notifications log entries like

```
Failed to send mobile app sessions ... fetch_error ... Error 1064 (42000): You have an error in your SQL syntax;
check the manual that corresponds to your MariaDB server version for the right syntax to use near
''$.last_removed_device_id', '')' at line 1
```

Cause: MariaDB's JSON function syntax/semantics differ from MySQL's, so a Sessions query referencing `Props.last_removed_device_id` is rejected; the push pipeline fails to fetch mobile sessions and notifications never deliver. Other features that touch JSON columns or other MySQL-only constructs will break similarly. Migration reference: `https://blogs.oracle.com/mysql/post/how-to-migrate-from-mariadb-to-mysql-80`.
