### mattermost-plugin-calls

**What**: Voice calling and screen sharing plugin
**Plugin ID**: `com.mattermost.calls`
**Min server**: 10.0.0
**Database**: PostgreSQL and MySQL (custom tables)

**Network requirements**:

| Service | Default Port | Setting | Protocol |
|---|---|---|---|
| RTC media (primary) | 8443 | `UDPServerPort` | UDP |
| RTC media (fallback) | 8443 | `TCPServerPort` | TCP |
| STUN server | 3478 | `ICEServersConfigs` | UDP |

- Default STUN: `stun:stun.global.calls.mattermost.com:3478`
- Valid port range: [80, 49151]
- TURN: requires `TURNStaticAuthSecret`, credentials expire in 240 minutes (configurable)
- `ICEHostOverride`: use when server is behind NAT (set to public IP)
- `ICEHostPortOverride`: when public-facing port differs from listen port

**RTCD (external RTC service)**:
- Optional, configured via `RTCDServiceURL`
- Minimum version: v0.17.0
- Offloads all call handling to external service
- Required for large-scale or HA deployments

**Participant limits**:

| Tier | Default Max |
|---|---|
| Self-hosted (no limit set) | 0 (unlimited) |
| Cloud Starter | 8 |
| Cloud Paid | 200 |

**Recording and transcription**:
- Recordings: disabled by default, duration range 15-180 min, quality: low/medium/high
- Transcription (Beta): whisper.cpp (default) or Azure, model sizes: tiny/base/small
- Live captions: requires both recordings AND transcriptions enabled
- Job service: `JobServiceURL` for recording/transcription jobs

### Calls pipeline reference

**End-to-end recording flow**: User clicks **Record** -> plugin creates a row in `calls_jobs` (`server/job_service.go:88`) -> offloader picks up the job and spawns a recorder container (passing `MM_CALLS_RECORDER_SITE_URL` if configured for private networks) -> recorder joins the call as a hidden client, records video+audio with FFmpeg, uploads to Mattermost as a file post -> plugin attaches the file to the original post in the channel. See `server/job_service.go:261-354` for the handoff. Per-component fragments: `claude-md/calls-offloader.md`, `claude-md/calls-recorder.md`, `claude-md/calls-transcriber.md`.

**Version compatibility matrix** (cross-checked against `plugin.json` and `upstream/calls-offloader/public/job/job.go`):

| Plugin requires | Min version |
|---|---|
| Offloader (`min_offloader_version`) | v0.9.0 |
| RTCD (`min_rtcd_version`) | v0.17.0 |

| Offloader requires | Min version |
|---|---|
| Recorder image (`MinSupportedRecorderVersion`) | v0.6.0 |
| Transcriber image (`MinSupportedTranscriberVersion`) | v0.1.0 |

These are **minimums** - newer versions are fine. Common upgrade failure: plugin upgraded without bumping offloader/RTCD; symptom is `minimum version check failed` in plugin logs.

**RTCD vs in-plugin RTC**: by default, RTC media flows through the plugin process on the app node. Set `RTCDServiceURL` to offload to a dedicated RTCD service. Use RTCD when:
- Running HA / multi-node Mattermost (in-plugin RTC pins media to whichever node the user lands on).
- More than ~50-100 active call participants total - app node CPU is the bottleneck.
- Running in K8s (recommended even at moderate load).

**Database tables**: `calls_channels`, `calls`, `calls_sessions`, `calls_jobs`. Migrations: 5 total at `server/db/migrations/{postgres,mysql}/`.

**Experimental features** (off by default): IPv6, simulcast, AV1 codec, data channel signaling, video in DMs

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Config struct and validation | `server/configuration.go` |
| RTCD connection logic | `server/rtcd.go` |
| Call limits | `server/limits.go` |
| Session management | `server/session.go` |
| Database layer | `server/db/` |
| API endpoints | `server/api.go` |

### Common Investigation Patterns

**RTCD unreachable (`no host available`)**: Verify `RTCDServiceURL` is set and resolvable from the app node; check that outbound traffic to RTCD's API port is open. RTCD itself listens on UDP/TCP 8443 for media plus an HTTP signaling port. If running RTCD in K8s, confirm the Service `targetPort` matches the RTCD pod and `RTCDServiceURL` uses cluster DNS.

**ICE host override needed (peers can't connect from outside)**: NAT'd RTC server. Set `ICEHostOverride` to the public IP and `ICEHostPortOverride` if the public-facing port differs from the listen port. Test with the WebRTC samples (`trickle-ice`) from outside the network.

**Recording / transcription job stuck**: Check `JobServiceURL` is reachable. Inspect the `calls_jobs` table for state. If using offloader, confirm the offloader pod can pull the recorder/transcriber images and that S3-compatible storage credentials are valid.

**Audio-only fallback (no video)**: Usually a UDP-blocked client falling back to TCP at 8443. Verify both UDP and TCP are open. If only TCP works, the experience is degraded but functional.

### Calls Plugin Errors

| Error Message | Cause | Resolution |
|---|---|---|
| `no host available` | RTCD unreachable or not configured | Verify `RTCDServiceURL`, check network/firewall, ensure RTCD is running |
| `minimum version check failed` | RTCD version < v0.17.0 | Upgrade RTCD to v0.17.0+ |
| `UDPServerPort is not valid: N is not in allowed range [80, 49151]` | Port out of valid range | Use a port between 80 and 49151 |
| `TCPServerPort is not valid: N is not in allowed range [80, 49151]` | Port out of valid range | Use a port between 80 and 49151 |
| `TURNStaticAuthSecret should be set` | TURN configured without auth secret | Set `TURNStaticAuthSecret` in plugin config |
| `group calls not allowed` | License or config restriction | Check license tier; verify `MaxCallParticipants` setting |
| `failed to resolve URL` | RTCD DNS resolution failure | Verify DNS for RTCD service URL |
| `MaxCallParticipants is not valid` | Negative value configured | Set to 0 (unlimited) or a positive integer |
