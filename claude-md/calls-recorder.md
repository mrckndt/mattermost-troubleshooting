### calls-recorder

**What**: Headless-browser recorder for Mattermost Calls; runs in a Docker container using Chromium and FFmpeg
**Stack**: Go, Chromium (chromedp), FFmpeg, Xvfb display server
**Min server**: 7.6 with Mattermost Calls plugin installed
**Primary use**: Invoked by `calls-offloader` to record call audio and video

**Pipeline reference**: end-to-end recording flow + cross-component version matrix in `claude-md/mattermost-plugin-calls.md > Calls pipeline reference`.

**Configuration (env vars)**:

| Variable | Required | Default | Range / Notes |
|---|---|---|---|
| `SITE_URL` | Yes | - | Mattermost server URL, no path |
| `CALL_ID` | Yes | - | Channel ID (26-char) |
| `POST_ID` | Yes | - | Post ID to attach recording (26-char) |
| `RECORDING_ID` | Yes | - | Job ID tracking the recording (26-char) |
| `AUTH_TOKEN` | Yes | - | Bot auth token (26-char) |
| `WIDTH` | No | 1920 | 1280-3840 px |
| `HEIGHT` | No | 1080 | 720-2160 px |
| `VIDEO_RATE` | No | 1500 | 500-10000 kbps |
| `AUDIO_RATE` | No | 64 | 32-320 kbps |
| `FRAME_RATE` | No | 30 | 10-60 fps |
| `VIDEO_PRESET` | No | fast | fast / faster / veryfast / superfast / ultrafast (H.264 speed) |
| `OUTPUT_FORMAT` | No | mp4 | mp4 only |
| `DEV_MODE` | No | false | Disables auth validation for testing |

**Network requirements**:
- Outbound HTTPS to Mattermost server (auth, uploads, job status posting).
- Chromium reaches `SITE_URL` from inside the container.
- Unix socket `/tmp/progress.sock` for FFmpeg progress monitoring.

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Config loading and validation | `cmd/recorder/config/config.go` |
| Browser automation (chromedp) | `cmd/recorder/recorder.go` (`runBrowser`) |
| FFmpeg transcoder setup | `cmd/recorder/recorder.go` (`runTranscoder`) |
| Recording upload + retry logic | `cmd/recorder/upload.go` (`publishRecording`) |
| Job status reporting | `cmd/recorder/job.go` |
| OS / kernel requirements check | `cmd/recorder/utils.go` (`checkOSRequirements`) |

### Common Investigation Patterns

**Browser fails to initialise (`timed out waiting for ready event` / `failed to poll for client initialization`)**: verify `SITE_URL` is reachable from inside the container, `AUTH_TOKEN` belongs to a bot user with Calls plugin access, and the Calls plugin is enabled. Inspect browser console output in container logs.

**Recording stuck during upload (`max retry attempts reached`)**: Mattermost server may be enforcing `FileSettings.MaxFileSize`. Recordings exceeding the limit retry with chunking (up to 20 attempts, exponential backoff). Check disk space on the server and confirm the bot's API token is still valid.

**Kernel capability failure (`kernel.unprivileged_userns_clone should be enabled`)**: the container needs user namespaces. On the host: `sysctl kernel.unprivileged_userns_clone=1`. See `cmd/recorder/utils.go` for the runtime check.

### Calls-Recorder Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `config cannot be empty` | Required env var missing | Set `SITE_URL`, `CALL_ID`, `POST_ID`, `RECORDING_ID`, `AUTH_TOKEN` |
| `CallID parsing failed` / `PostID parsing failed` / `RecordingID parsing failed` / `AuthToken parsing failed` | ID not 26-char alphanumeric | Use valid Mattermost IDs |
| `SiteURL parsing failed: invalid scheme` | URL not http / https | Use full URL with scheme |
| `SiteURL parsing failed: invalid path` | URL has a path component | Drop trailing path |
| `Width/Height/VideoRate/FrameRate value is not valid` | Outside accepted range | See env-var range column above |
| `timed out waiting for ready event` | Browser connect timeout | Check `SITE_URL`, `AUTH_TOKEN`, plugin enabled |
| `timed out waiting for transcoder to start` | FFmpeg failed to start | Check Xvfb running, kernel sysctl |
| `max retry attempts reached, exiting` | Upload failures after 20 retries | Check server disk, `MaxFileSize`, API connectivity |
| `kernel.unprivileged_userns_clone should be enabled` | Container lacks user namespaces | Enable on host (`sysctl kernel.unprivileged_userns_clone=1`) |
