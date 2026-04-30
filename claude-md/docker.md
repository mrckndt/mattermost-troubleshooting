### docker

**What**: Docker Compose recipes for Mattermost (app + PostgreSQL + nginx reverse proxy with TLS). NOT the Docker image build itself.
**Stack**: Docker Compose, `mattermost/mattermost-{enterprise,team}-edition` images, PostgreSQL, nginx

**Key compose files / scripts**:
- `docker-compose.yml` - base services (PostgreSQL, Mattermost).
- `docker-compose.nginx.yml` - nginx reverse-proxy overlay, TLS termination.
- `docker-compose.without-nginx.yml` - direct app port exposure (no reverse proxy).
- `env.example` - environment template with all configurable variables.
- `scripts/issue-certificate.sh` - Let's Encrypt provisioning helper.
- `scripts/upgrade-postgres.sh` - PostgreSQL major-version upgrade with data migration.
- `nginx/conf.d/default.conf` - nginx vhost config (WebSocket, proxy cache).

**Configuration (env vars in `.env`)**:
- **Database**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_IMAGE_TAG`, `POSTGRES_DATA_PATH`.
- **Mattermost app**: `MATTERMOST_IMAGE`, `MATTERMOST_IMAGE_TAG`, `MATTERMOST_CONFIG_PATH`, `MATTERMOST_DATA_PATH`, `MATTERMOST_LOGS_PATH`, `MATTERMOST_PLUGINS_PATH`, `MATTERMOST_CLIENT_PLUGINS_PATH`, `MATTERMOST_BLEVE_INDEXES_PATH`, `MATTERMOST_CONTAINER_READONLY`.
- **App networking**: `MM_SQLSETTINGS_DRIVERNAME`, `MM_SQLSETTINGS_DATASOURCE`, `MM_SERVICESETTINGS_SITEURL`, `MM_BLEVESETTINGS_INDEXDIR`, `APP_PORT`, `CALLS_PORT`.
- **nginx**: `NGINX_IMAGE_TAG`, `NGINX_CONFIG_PATH`, `NGINX_DHPARAMS_FILE`, `CERT_PATH`, `KEY_PATH`, `HTTP_PORT`, `HTTPS_PORT`, `DOMAIN`.
- **Container runtime**: `TZ`, `RESTART_POLICY`.

See `env.example` for defaults and descriptions.

**Network requirements**:
- nginx compose: HTTP 80 + HTTPS 443 to host; internal upstream `mattermost:8065`.
- without-nginx: app port (default 8065, overridable via `APP_PORT`) bound to host.
- Calls/WebRTC: UDP/TCP `CALLS_PORT` (default 8443).
- nginx routes `/api/v*/websocket` with `Upgrade` / `Connection` headers and `proxy_read_timeout` >= 90s (`nginx/conf.d/default.conf`).

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Base compose | `docker-compose.yml` |
| Nginx overlay | `docker-compose.nginx.yml` |
| Without-nginx overlay | `docker-compose.without-nginx.yml` |
| Nginx vhost | `nginx/conf.d/default.conf` |
| Env template | `env.example` |
| Cert / key paths | `CERT_PATH`, `KEY_PATH` (default `./volumes/web/cert/`) |
| Cert issuance helper | `scripts/issue-certificate.sh` |
| Postgres upgrade helper | `scripts/upgrade-postgres.sh` |

### Common Investigation Patterns

**WebSocket drops after 60s**: Default nginx idle timeout. In `nginx/conf.d/default.conf`, the websocket `location` block needs `proxy_read_timeout` >= 90s plus `Upgrade` / `Connection` headers. If using an external reverse proxy in front, check its idle timeout (must exceed 60s).

**Plugins not persisting / writable**: `MATTERMOST_PLUGINS_PATH` and `MATTERMOST_CLIENT_PLUGINS_PATH` must be writable host volumes mounted to `/mattermost/plugins` and `/mattermost/client/plugins`. The container runs as UID 2000; verify ownership: `chown -R 2000:2000 ./volumes/app/mattermost`.

**Postgres init hangs / connect failures**: `MM_SQLSETTINGS_DATASOURCE` must use the credentials from `.env` and host `postgres` (Docker DNS). Default template: `postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}?sslmode=disable`. `depends_on` ensures postgres starts before mattermost, but does NOT wait for readiness - the app container retries.

### Docker-Compose Errors

| Error | Likely cause | Resolution |
|---|---|---|
| Cert volume not found (`/cert.pem`, `/key.pem`) | `CERT_PATH` / `KEY_PATH` not set or files don't exist | Run `scripts/issue-certificate.sh` or mount valid PEM files |
| Nginx 403 on ACME challenge | Missing dhparams or webroot volume | Generate: `openssl dhparam -out dhparams4096.pem 4096`. Mount `shared-webroot` |
| `sslmode=disable` warning | Default in `env.example` | For production: set `sslmode=require` and configure Postgres TLS |
| Plugin upload fails in read-only mode | `MATTERMOST_CONTAINER_READONLY=true` | Set to `false` (default). Read-only blocks plugin uploads and `root.html` regeneration |
