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
- `ICEHostOverride`: use when server is behind NAT (set to public IP). Accepted formats per `plugins-configuration-settings.rst`: a single IP (`10.0.0.1`), a single hostname/FQDN (`calls.example.tld`), or (starting plugin v0.17.0) a comma-separated list of `externalAddr/internalAddr` pairs (`10.0.0.1/172.0.0.1,10.0.0.2/172.0.0.2`). Note: a hostname is resolved on the Mattermost host - if that resolution differs from what clients see, connectivity fails. When in doubt, use an IP.
- `ICEHostPortOverride`: when public-facing port differs from listen port (applies to both UDP and TCP host candidates)

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
- Recordings: disabled by default. `MaxRecordingDuration` valid range [15, 180] min, default `60` (constants in `server/configuration.go`; doc default also `60` in `plugins-configuration-settings.rst`). Quality: `Low` / `Medium` / `High`, default **Medium**.
- Transcription (Beta): whisper.cpp (default) or Azure. Plugin's `transcribermodelsize` setting exposes Tiny / Base / Small (default Base) - the underlying transcriber binary supports `medium` / `large` too but they are not exposed via System Console.
- Live captions (Experimental): requires recordings AND transcriptions enabled. Defaults: `livecaptionsmodelsize=Tiny`, `livecaptionsnumtranscribers=1`, `livecaptionsnumthreadspertranscriber=2`. Constraint: `LiveCaptionsNumTranscribers * LiveCaptionsNumThreadsPerTranscriber` must be in `[1, numCPUs]`. Default language `en`.
- Job service: `JobServiceURL` (env `MM_CALLS_JOB_SERVICE_URL`) for recording/transcription jobs. Self-registers on first connect using the Mattermost diagnostic ID, or accepts explicit credentials via `http://clientID:authKey@host` syntax / `MM_CALLS_JOB_SERVICE_CLIENT_ID` + `MM_CALLS_JOB_SERVICE_AUTH_KEY` env vars.

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

**RTCD vs in-plugin RTC** (per `calls-deployment-guide.md` 1.2 "Media Service: RTCD or Integrated"):
- **Integrated** (in-plugin): the Calls plugin runs the media service inside the Mattermost server. Up to ~50 *Total Users* per the deployment guide.
- **RTCD** (recommended for production): a dedicated service, set via `RTCDServiceURL`. Required when **deploying on Kubernetes** (only supported model per `calls-kubernetes.md`), or when *Total Users* > 50, or for HA / multi-node Mattermost where in-plugin RTC would pin media to one app node. Requires Enterprise license.

License tiers (per the deployment guide "Deployment Infrastructure Requirements"): Mattermost Entry / Team Edition cover 1:1 calls + screen sharing (40-min cap). Professional covers group calls (no time limit). Enterprise / Enterprise Advanced add RTCD (50+ users, prod reliability) and Recording / Transcription / Live Captions.

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

**Authoritative customer-facing docs**: deployment + decision-tree in `https://docs.mattermost.com/administration-guide/configure/calls-deployment-guide.html`; per-setting reference in `https://docs.mattermost.com/administration-guide/configure/plugins-configuration-settings.html` (Calls section). RTCD / offloader / K8s specifics: `claude-md/rtcd.md`, `claude-md/calls-offloader.md`, `claude-md/calls-recorder.md`, `claude-md/calls-transcriber.md`. Cite the published URLs in customer replies, not local paths.

**Metrics endpoint**: `http://<MATTERMOST_HOST>:8067/plugins/com.mattermost.calls/metrics` (verified at `server/api_router.go:26`). The deployment guide's monitoring section also lists the RTCD scrape target (`<RTCD_HOST>:8045/metrics`) and Grafana dashboard ID `23225` for the canonical Calls dashboard.

**Job Service URL caveat** (`plugins-configuration-settings.rst` line 712): from Calls v0.25, `MM_CALLS_RECORDER_SITE_URL` and `MM_CALLS_TRANSCRIBER_SITE_URL` (set on the Mattermost server, not the offloader) override the SiteURL that recorder / transcriber jobs use to call back. Use these in private-network deployments to keep job traffic off the public network. May require expanding `ServiceSettings.AllowCorsFrom` to match.

### Common Investigation Patterns

**nginx in front of Mattermost (don't proxy 8443)**: Per `calls-deployment-guide.md`: "Port 8443 must be opened directly on the server running the media service (RTCD or Integrated) - not on NGINX. Port 443 is the only port NGINX needs to handle for Calls." Putting `8443` (UDP/TCP) behind nginx silently breaks media even when signaling on 443 still works.

**RTCD unreachable (`no host available`)**: Verify `RTCDServiceURL` is set and resolvable from the app node; check that outbound traffic to RTCD's API port (8045) is open. RTCD itself listens on UDP/TCP 8443 for media. If running RTCD in K8s, confirm the Service `targetPort` matches the RTCD pod and `RTCDServiceURL` uses cluster DNS. The plugin self-registers on first connect and stores the auth key in the database; subsequent restarts reuse it.

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
