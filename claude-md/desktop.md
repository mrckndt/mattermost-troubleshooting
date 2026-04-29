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
