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

### Mobile Client Errors

| Error / Code | Cause | Resolution |
|---|---|---|
| Certificate error -103, -104, -105, -108 | Client certificate import failure | Re-import client certificate, check format (PKCS#12) |
| Certificate error -200 | Client certificate missing | Install client certificate on device |
| Certificate error -299 | Server certificate invalid | Fix server certificate (not self-signed, valid chain) |
| Certificate error -298 | Server trust evaluation failed | Check certificate chain, CA trust store |
| Push notifications silently dropped | Push proxy returned `NOT_AVAILABLE` | Check `EmailSettings.PushNotificationServer`, verify proxy is reachable |
| WebSocket TLS handshake error (code 1015) | TLS issue on WebSocket connection | Check TLS configuration, certificate validity |
