### desktop

**What**: Electron-based desktop client for Windows, macOS, Linux
**Stack**: Electron, TypeScript/React, webpack
**Config versions**: V0 through V4 (current)

**Config storage locations**:

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\Mattermost` |
| macOS | `~/Library/Application Support/Mattermost` |
| Linux | `~/.config/Mattermost` |

Custom data directory via CLI flag: `--data-dir`

**Logging**: electron-log library, default level `info`, log files in the user data directory (same as config).

**Enterprise deployment**: GPO support on Windows (`resources/windows/gpo/`), MDM profiles on macOS (`resources/mac/mdm/`).

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Config types and versions | `src/types/config.ts` |
| Default preferences | `src/common/config/defaultPreferences.ts` |
| Logger | `src/common/log.ts` |
| Window management | `src/app/windows/baseWindow.ts` |
| Notifications/badge | `src/app/system/badge.ts` |

### Common Investigation Patterns

**Certificate-trust issues (self-signed / corporate CA)**: Desktop uses the OS certificate store. Customer must install the CA cert at the OS level (not just in the browser). For client-cert auth, follow the platform-specific import flow. Self-signed certs without an OS-level trust anchor are rejected.

**Auto-launch / start-with-OS misbehaving**: Settings -> "Start app on login" toggles the platform-specific autolaunch entry (`launchctl` plist on macOS, registry Run key on Windows, `~/.config/autostart/` on Linux). MDM/GPO policies can override or hide this toggle.

**Multi-server config not syncing**: Each server has a separate config entry under the user data directory. If servers disappear after upgrade, check the config-version migration ran (`src/types/config.ts` V0->V4). Manual edits to `config.json` need a relaunch.

**IPC channel registry** (for cross-window or renderer-main communication issues): all registered channels exposed to renderers are in `src/app/preload/externalAPI.ts` (40+ channels including `NOTIFY_MENTION`, `SESSION_EXPIRED`, `CALLS_*`). Main process window management: `src/app/windows.ts`. Renderer code must use this preload API - direct Node.js access is blocked.

**MDM / GPO enforced fields**: Windows GPO (`resources/windows/gpo/mattermost.admx`) and macOS MDM (`resources/mac/mdm/example-managed-preferences.plist`) both enforce the same three policies: `EnableAutoUpdater` (block updates), `EnableServerManagement` (lock server list), `DefaultServerList` (pre-configure servers). Only these three are managed; all other config is user-controlled. Affected settings appear locked in the desktop UI.
