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

#### Browser-API bugs leave no server-side trace

**Symptom:** a browser-run feature (notifications, downloads, clipboard, paste, drag-and-drop, uploads, service workers,
permission prompts) misbehaves, but server logs and config are clean.

**Possible cause:** the webapp passes wrong arguments to the browser API (e.g. content landing in a notification `tag` or a
download filename). Nothing reaches the server, so no log line or config key points at it.

**Diagnosis:** read the webapp call site against the browser API spec before concluding no Mattermost-side fix exists.

#### CVE findings: prepackaged plugins ship their own webapp bundles

**Symptom:** a scanner flags a vulnerable JS library against a Mattermost version, but `webapp/package.json` at that tag
already has the patched dependency. The finding looks like a false positive; usually it is not.

**Cause:** each prepackaged plugin builds its own webapp bundle from its own `node_modules`. The server serves it from the
same origin as the core webapp, at `/static/<plugin-id>/<plugin-id>_<hash>_bundle.js` (`ClientManifest` in
`server/public/model/manifest.go`; the hash is the FNV-1a hash of the bundle). Separate builds, lockfiles and repos:
patching the core webapp dependency does nothing for the plugin bundles.

**Diagnosis:**

- **Plugin list:** read it from the customer's tag, never `master`; pinned versions move between releases:
  `git -C "$PROJECT_ROOT/upstream/mattermost" show v<version>:server/Makefile | grep PLUGIN_PACKAGES`.
  `FIPS_ENABLED=true` replaces the list wholesale with playbooks, agents and boards, so a FIPS build prepackages no
  calls, github or jira bundle at all.
- **Flagged URL:** map it to a real asset; `GET /api/v4/plugins/webapp` lists `.[].webapp.bundle_path` for every bundle
  the server actually serves.
- **Owning plugin:** check it at its pinned tag, not its default branch. Report "fixed in plugin vX.Y.Z" and "first
  Mattermost version that prepackages it" separately; if the second is "none yet", upgrading does not clear the finding.
- **Runtime vs build-time:** a `webapp/package-lock.json` entry with `"dev": true` is reachable only from devDependencies
  and never reaches a browser. "Present in the lockfile" and "served to users" are different claims; say which one.
- **Bundled vs external:** plugins list react, redux, react-intl and similar in `externals` (`webapp/webpack.config.js`)
  to reuse the host webapp's copy; anything else is compiled into the bundle.
- **Tree-shaking:** CommonJS dependencies are not tree-shaken. `import {debounce} from 'lodash'` bundles the whole library,
  version string included, and that string is what fingerprinting scanners detect. "Only one safe function is called"
  does not clear the finding; report reachability as a separate, weaker claim, and only after checking the plugin's
  transitive runtime deps rather than just its own source.

**Trap:** `dataminr` is prepackaged from v12.0 and is the only prepackaged plugin with no `upstream/` clone (not in
`.agents/config/repos.json`). Check it through the GitHub MCP instead of concluding it is unaffected.

This generalizes past CVEs: when core webapp source does not explain a browser-side symptom, the plugin bundles are the
next place to look, not the last.
