### mattermost-mobile

**What**: React Native mobile app for iOS and Android
**Stack**: React Native (New Architecture disabled), WatermelonDB/SQLite, TypeScript
**Min server**: ESR 10.11.0+
**Database**: Dual WatermelonDB/SQLite (client-side only, no server-side tables)

**Dual database system**:
- **App Database**: global state, server list (`app/database/models/app/`)
- **Server Database**: one per connected server for channels, users, posts (`app/database/models/server/`)
- **DatabaseManager** singleton at `app/database/manager/index.ts`

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Push notification init | `app/init/push_notifications.ts` |
| Push proxy verification | `app/utils/push_proxy.ts` |
| WebSocket client | `app/client/websocket/index.ts` |
| Network manager | `app/managers/network_manager.ts` |
| Database manager | `app/database/manager/index.ts` |
| Error handling | `app/utils/error_handling.ts`, `app/utils/errors.ts` |
| Logging utilities | `app/utils/log.ts` |

**Push notifications**:
- Library: `react-native-notifications`
- Push proxy verification states: `VERIFIED`, `NOT_AVAILABLE`, `UNKNOWN`
- Self-compiled apps MUST run their own Mattermost Push Notification Service (MPNS)
- Unverified notifications are silently dropped

**Certificate handling**:
- Self-signed certificates are **NOT supported**
- Client certificate import error codes: -103, -104, -105, -108
- Client certificate missing: -200
- Server certificate invalid: -299
- Server trust evaluation failed: -298

**WebSocket constants** (from `app/client/websocket/index.ts`):
- `MAX_WEBSOCKET_FAILS`: 7
- `WEBSOCKET_TIMEOUT`: 30 seconds
- `MIN_WEBSOCKET_RETRY_TIME`: 3 seconds
- `MAX_WEBSOCKET_RETRY_TIME`: 5 minutes
- `PING_INTERVAL`: 30 seconds
- Network: one Client per server via NetworkManager, exponential retry (3 retries)

### Common Investigation Patterns

**Push proxy reports `NOT_AVAILABLE`**: Notifications are silently dropped client-side. Verify `EmailSettings.PushNotificationServer` points to a reachable HPNS or self-hosted MPNS, and that `EmailSettings.SendPushNotifications=true`. Self-compiled mobile apps MUST run their own MPNS - HPNS only accepts traffic from the official app builds.

**Deep links not opening the app**: Custom-domain deployments need `ServiceSettings.SiteURL` to match the URL users tap. The mobile app validates the incoming URL's host via `sanitizeUrl()` / `isParsableUrl()` in `app/utils/url/index.ts`. If SiteURL has a trailing slash mismatch or the scheme differs, the link falls through to the browser. Deep-link scheme/path constants: `app/constants/deep_linking.ts`.

**Sentry breadcrumb fields** (when customer shares a crash report): captured automatically from every `logError()` / `logWarning()` call (`app/utils/log.ts`, `app/utils/error_handling.ts`). Fields: `level`, `message`, `type`, `data` (key-value context). No persistent log file exists on device by default - Sentry is the primary crash-data source for official builds.

**WebSocket reconnect storm after server restart**: Clients try up to 7 times with backoff (3s -> 5min). On the server side this surfaces as a burst of "user access token" warnings (see `mattermost.md` deep-dive on session resolution); harmless if it tapers off. If it doesn't taper, inspect the network manager and load-balancer idle timeout (must be >60s).

### Mobile Client Errors

| Error / Code | Cause | Resolution |
|---|---|---|
| Certificate error -103, -104, -105, -108 | Client certificate import failure | Re-import client certificate, check format (PKCS#12) |
| Certificate error -200 | Client certificate missing | Install client certificate on device |
| Certificate error -299 | Server certificate invalid | Fix server certificate (not self-signed, valid chain) |
| Certificate error -298 | Server trust evaluation failed | Check certificate chain, CA trust store |
| Push notifications silently dropped | Push proxy returned `NOT_AVAILABLE` | Check `EmailSettings.PushNotificationServer`, verify proxy is reachable |
| WebSocket TLS handshake error (code 1015) | TLS issue on WebSocket connection | Check TLS configuration, certificate validity |
