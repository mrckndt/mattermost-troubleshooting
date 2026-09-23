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

#### Pin/unpin blocked by PostEditTimeLimit (v11.7.0+)

**Symptom:** users cannot pin/unpin a post older than `ServiceSettings.PostEditTimeLimit` (e.g. 172800 = 2 days); newer posts pin fine. Debug log on `/pin` or `/unpin`:

```
"msg":"Post edit is only allowed for 172800 seconds...","err_where":"saveIsPinnedPost","path":"/api/v4/posts/<id>/pin","http_code":400
```

**Cause:** v11.7.0 (PR #35638, commit `a19cc4b909`) extended the edit time limit from message-text-only to any post mutation, including `IsPinned`. `saveIsPinnedPost` now calls `postEditTimeLimitExpired` (`server/channels/api4/post.go:1349`); before 11.7.0 the pin/unpin endpoints had no time-limit check. Still present on `master`. Re-pinning an already-pinned post is exempt (`post.go:1343`).

- **Not permissions/license:** failure is the time-limit `AppError` (HTTP 400), not a 403. The pin path checks read-channel permission plus the time limit only; it ignores `AllowEditPost`/`edit_post`, so changing edit permissions does not help.

**Fix:** raise `ServiceSettings.PostEditTimeLimit` in `config.json` to a window that covers expected pinning, or set `-1` for unlimited. Read live via the config watcher; no restart. config.json-only (System Console control deprecated). Tradeoff: the same setting governs message editing, so raising it also widens the edit window.

#### `upstream/docs` is a full monorepo clone pinned to `master`

Docs now live in-tree at `docs/main`/`docs/develop`. `v11.10` is the first release with `docs/` present - older tags have none. Never `/git-switch docs` off `master`. Once every supported version is `>= v11.10`, retire this clone and read docs from the version-aligned `upstream/mattermost` instead.

#### CVE and dependency findings: the page is core webapp plus one bundle per prepackaged plugin

**Symptom:** a scanner flags a vulnerable JS library against a Mattermost version, but `webapp/package.json` at that tag shows the dependency already patched, so the finding reads as a false positive. It usually is not.

**Cause:** every prepackaged plugin builds its own `webapp/` bundle from its own `node_modules`, and the server serves it from the same origin as the core webapp at `/static/<plugin-id>/<plugin-id>_<hash>_bundle.js` (assembled in `server/public/model/manifest.go:269`; the hash is the FNV-1a hash of the bundle). Separate builds, separate lockfiles, separate repos: patching the core webapp dependency does nothing for the plugin bundles.

**Working one:**

- **Take the plugin list from the customer's tag, never `master`:** `git -C "$PROJECT_ROOT/upstream/mattermost" show v<version>:server/Makefile | grep PLUGIN_PACKAGES`. Pinned versions move between releases. `FIPS_ENABLED=true` replaces the list wholesale with a three-plugin subset (playbooks, agents, boards), so a FIPS build prepackages no calls, github or jira bundle at all.
- **Map the flagged URL to a real asset:** `GET /api/v4/plugins/webapp` returns `.[].webapp.bundle_path` for every bundle a running server actually serves.
- **Check the owning plugin at its pinned tag,** not its default branch, and report two facts separately: "fixed in plugin vX.Y.Z" and "first Mattermost version that prepackages it". The second can be "none yet", in which case upgrading does not clear the finding.
- **Runtime vs build-time:** in the plugin's `webapp/package-lock.json`, an entry with `"dev": true` is reachable only from devDependencies and never reaches a browser. "Present in the lockfile" and "served to users" are different claims; say which one you mean.
- **Check `webapp/webpack.config.js` `externals`:** plugins externalize react, redux, react-intl and similar to reuse the host webapp's copy. Anything not listed is compiled into the plugin bundle.
- **CommonJS dependencies are not tree-shaken:** `import {debounce} from 'lodash'` still bundles the whole library, version string included, and that string is what external fingerprinting scanners detect. "We only call one safe function" does not clear the finding; report reachability as a separate, weaker claim, and only after checking the plugin's transitive runtime deps rather than just its own source.

**Trap:** `dataminr` is the only prepackaged plugin with no `upstream/` clone (private repo, see `repos.json`). Reach it through the GitHub MCP instead of concluding it is unaffected.

This generalizes past CVEs. When core webapp source does not explain a reported browser-layer symptom, the plugin bundles are the next place to look, not the last. Found on a ticket where the core webapp lodash bump landed correctly in 11.7.11 while the prepackaged playbooks and boards bundles kept serving the vulnerable copy.
