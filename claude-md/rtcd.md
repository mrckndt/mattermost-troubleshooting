### rtcd

**What**: Real-Time Communication Daemon - external WebRTC / media-routing service for Mattermost Calls. Offloads RTC handling from app nodes; required (or strongly recommended) for HA, K8s, and high-participant deployments.
**Stack**: Go, Pion WebRTC, embedded BoltDB-style k/v store, HTTP + WebSocket signaling
**Used by**: `mattermost-plugin-calls` via `RTCDServiceURL`. See `claude-md/mattermost-plugin-calls.md` for the plugin-side toggle and version compatibility matrix (plugin requires `min_rtcd_version` v0.17.0+).

**Configuration**: TOML file (`config/config.sample.toml`) or env vars with prefix `RTCD_` (full list in `docs/env_config.md`). Key fields:

| Section | Field | Default | Purpose |
|---|---|---|---|
| `api.http` | `listen_address` | `:8045` | HTTP / WebSocket signaling API (the port the Calls plugin connects to) |
| `api.http.tls` | `enable` / `cert_file` / `cert_key` | off | TLS for the signaling API |
| `api.security` | `allow_self_registration` | `false` | If true, clients (Mattermost instances) auto-register on first connect; safe only on internal networks |
| `api.security` | `enable_admin` / `admin_secret_key` | off | Enables an admin client that can pre-create credentials via `/register` |
| `api.security.session_cache` | `expiration_minutes` | `1440` (24h) | Bearer-token lifetime |
| `rtc` | `ice_address_udp` / `ice_address_tcp` | `""` (all interfaces) | Local listen IPs for media; supports comma-separated multi-IP |
| `rtc` | `ice_port_udp` / `ice_port_tcp` | `8443` | Media ports (UDP preferred, TCP fallback) |
| `rtc` | `ice_host_override` | (empty) | Public IP advertised in candidates; needed behind NAT. Supports `ext1/int1,ext2/int2` mapping syntax. |
| `rtc` | `ice_host_port_override` | (empty) | Override public-facing port; supports per-local-IP map (`localIPA/8443,localIPB/8444`) for multi-pod K8s |
| `rtc` | `ice_servers` | `[]` | STUN / TURN entries (`{urls, username, credential}`) |
| `rtc.turn` | `static_auth_secret` | (empty) | HMAC secret for short-lived TURN credentials |
| `rtc.turn` | `credentials_expiration_minutes` | `1440` | TURN credential lifetime |
| `rtc` | `enable_ipv6` | `false` | Dual-stack mode |
| `rtc` | `udp_sockets_count` | dynamic (CPUs * 100) | Listening UDP sockets per local address; raise for throughput, lower if hitting fd limits |
| `rtc` | `nack_buffer_size` | `256` (~8.5s @30fps) | Per-SSRC NACK retransmission buffer; power of 2 (32-8192) |
| `rtc` | `nack_disable_copy` | `true` | Set to `false` for production stability (default `true` is faster but can crash on ring-buffer wrap-around) |
| `store` | `data_source` | `/tmp/rtcd_db` | Path for the embedded k/v store of registered clients + hashed credentials |
| `logger` | `enable_console` / `enable_file` / `console_level` / `file_level` / `file_location` | console on, file on, INFO/DEBUG, `rtcd.log` | Logging |

Env-var override format: TOML path uppercased and underscored, prefixed `RTCD_`. E.g. `api.security.allow_self_registration` -> `RTCD_API_SECURITY_ALLOWSELFREGISTRATION`.

**Network requirements**:

| Service | Port / Protocol | Direction | Notes |
|---|---|---|---|
| Signaling API (HTTP/WS) | TCP `8045` | Mattermost (Calls plugin) -> rtcd | Set `RTCDServiceURL` in plugin to `http://<host>:8045` (or `https://...` if TLS enabled). Supports `http://clientID:authKey@host` syntax for credentials. |
| Media (preferred) | UDP `8443` | Clients <-> rtcd, bidirectional | Must be open end-to-end through firewalls / NAT |
| Media (fallback) | TCP `8443` | Clients <-> rtcd | When client UDP blocked |
| STUN (if used) | UDP `3478` | rtcd -> STUN server | Default plugin STUN: `stun.global.calls.mattermost.com:3478` |

**Authentication flow** (`docs/security.md`):
1. Self-register (if `allow_self_registration=true`): client POSTs `{clientID, authKey}` to `/register`; server stores bcrypt hash. Default Calls plugin uses the Mattermost `DiagnosticID` as `clientID` if none provided.
2. Admin-pre-registered (if `enable_admin=true`): an admin call via Basic Auth with `admin_secret_key` registers credentials before client connects.
3. Per-request auth: HTTP Basic (clientID + authKey) or Bearer (token from `/login`). Bearer expiration = `session_cache.expiration_minutes`.

Plugin-side credential injection: `MM_CALLS_RTCD_CLIENT_ID` and `MM_CALLS_RTCD_AUTH_KEY` env vars on Mattermost (alternative to embedding in `RTCDServiceURL`).

**HTTP API endpoints** (registered in `service/service.go`):

| Path | Method | Purpose |
|---|---|---|
| `/version` | GET | Build info; useful for liveness probes (`{build_hash, build_date, build_version, goVersion}`) |
| `/metrics` | GET | Prometheus metrics scrape endpoint (e.g. `rtcd_rtc_errors_total`, `rtcd_process_cpu_seconds_total`, `rtcd_process_resident_memory_bytes`) |
| `/register` | POST | Self-register a client (requires `allow_self_registration=true` or admin auth) |
| `/login` | POST | Exchange clientID+authKey for bearer token |
| `/unregister` | POST | Remove a client |
| `/system` | GET | System info (when admin enabled) |
| `/ws` | WS upgrade | Signaling channel for SDP / ICE candidates |

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Service entry point | `cmd/rtcd/` |
| Top-level service composition | `service/service.go` |
| Config struct + validation | `service/config.go` |
| HTTP API server (TLS, mux) | `service/api/` |
| Auth (basic, bearer, admin) | `service/auth/` |
| Embedded credential store | `service/store/` |
| WebRTC / media handling | `service/rtc/` |
| WebSocket signaling | `service/ws/` |
| Audit logging | `service/audit.go` |
| Config sample | `config/config.sample.toml` |
| Env var reference | `docs/env_config.md` |
| Getting started | `docs/getting_started.md` |
| Implementation overview | `docs/implementation.md` |
| Security architecture | `docs/security.md` |

**Authoritative customer-facing docs**: `https://docs.mattermost.com/administration-guide/configure/calls-rtcd-setup.html`, `https://docs.mattermost.com/administration-guide/configure/calls-deployment-guide.html`, `https://docs.mattermost.com/administration-guide/configure/calls-kubernetes.html`. RTCD-specific RST settings (e.g. `RTCDServiceURL`, `ICEHostOverride`, TURN auth secret) are in `https://docs.mattermost.com/administration-guide/configure/plugins-configuration-settings.html` under the Calls section. Local sources: `upstream/docs/source/administration-guide/configure/calls-{rtcd-setup,deployment-guide,kubernetes}.md`. Cite published URLs (not local paths) in customer replies.

**Connectivity self-test recipes** (from `calls-rtcd-setup.md` Validation section + `calls-deployment-guide.md` Phase 1.6):

```
# UDP path: clients -> RTCD on 8443 (stop rtcd first; it binds the same port)
sudo systemctl stop rtcd
# On RTCD host:
sudo ncat -u -l -k -p 8443 -c '/bin/cat'
# On client:
sudo nmap -sU -p 8443 RTCD_SERVER_IP    # expect "open"
sudo systemctl start rtcd

# TCP fallback: clients -> RTCD on 8443
nmap -p 8443 RTCD_SERVER_IP

# API: Mattermost server -> RTCD on 8045
nmap -p 8045 RTCD_SERVER_IP
curl http://RTCD_SERVER_IP:8045/version
# Expected: {"build_hash":"...","build_date":"...","build_version":"0.11.0","goVersion":"go1.20.4"}
```

`open` = pass; `closed` = listener missing; `filtered` = firewall blocking.

### Common Investigation Patterns

**Plugin can't connect to rtcd (`no host available` / dial error in plugin logs)**: Verify `RTCDServiceURL` resolves and reaches the rtcd `api.http.listen_address` (default 8045) from the app node. With `allow_self_registration=false`, the plugin's `clientID/authKey` must already exist in rtcd's store - check audit log or registered-clients dump. If running rtcd in Kubernetes, ensure the Service `targetPort` matches and that `http://...` (not `https://`) is used unless `api.http.tls.enable=true`.

**nginx / reverse proxy in front of RTCD (don't)**: nginx must NOT forward UDP `8443`. Per `calls-deployment-guide.md`: "Port 8443 must be opened directly on the server running the media service (RTCD or Integrated) - not on NGINX. Port 443 is the only port NGINX needs to handle for Calls." Putting RTCD behind a normal L7 proxy silently breaks media even though `/version` on `8045` may still respond.

**Media (audio/video) drops or one-way**: `ice_port_udp`/`ice_port_tcp` (default 8443) must be open bidirectionally between clients and rtcd. Behind NAT, `ice_host_override` must be the public IP. If only TCP works (audio fine, video laggy), UDP is being blocked somewhere upstream.

**K8s multi-node deployment**: Each rtcd pod typically advertises a different public IP. Use the `ice_host_override` mapping form (`pubA/localA,pubB/localB`) so the same config can be passed to all pods, with each pod auto-selecting the override that matches its local IP. `ice_host_port_override` supports the same per-local-IP mapping for NLB-fronted setups.

Per `calls-kubernetes.md`, each `rtcd` process must live on a **dedicated Kubernetes node** - traffic does not flow through a standard ingress, it goes directly to the pod. The recommended pattern is one external IP per rtcd instance / node. A single call is hosted entirely on one rtcd pod and does not migrate. Use the official Helm chart at `mattermost/mattermost-rtcd`; the AWS NLB UDP backend annotation example from the doc is `service.beta.kubernetes.io/aws-load-balancer-backend-protocol=udp`.

**Horizontal scaling** (`calls-rtcd-setup.md` Horizontal Scaling): deploy multiple RTCD instances each with their own IP, point a DNS record at all of them, set up health checks, and configure the Mattermost **RTCD Service URL** to the DNS name. When a call starts, the Mattermost server picks the RTCD with the lowest CPU - all participants of that call are pinned to that one RTCD; a single call cannot span multiple RTCD servers.

**File descriptor exhaustion**: With high `udp_sockets_count` (default `numCPU * 100`) the process can open thousands of fds. Tune the systemd unit (`LimitNOFILE=`) or lower `udp_sockets_count` if the host can't accommodate.

**Memory-corruption crashes / segfaults under load**: The default `nack_disable_copy=true` is faster but unsafe. For production stability set `RTCD_RTC_NACKDISABLECOPY=false`.

**Restart wipes registered clients**: `store.data_source` (default `/tmp/rtcd_db`) is on tmpfs / cleared on reboot. Mount a persistent volume; on systemd, `/var/lib/rtcd`. On Docker, mount a volume to that path.

**Version compatibility**: plugin's `min_rtcd_version` is the floor (currently v0.17.0; see `mattermost-plugin-calls.md`). After upgrading the plugin, also bump rtcd; symptom of skew is `minimum version check failed` in plugin logs at startup.

**TURN credentials not rotating**: rtcd issues short-lived HMAC credentials based on `turn.static_auth_secret`. If the TURN server uses a different secret, all relayed media fails. Set the same secret on both sides; default lifetime 240 minutes (`credentials_expiration_minutes`).

### rtcd Errors

| Error / Symptom | Likely Cause | Resolution |
|---|---|---|
| `failed to register client` (HTTP 401) | `allow_self_registration=false` and clientID not pre-registered | Pre-register via admin client, or set self-registration on for internal networks |
| `failed to register client` (HTTP 409) | clientID already exists with a different authKey | Use `/unregister` first, or pick a fresh clientID |
| Plugin log: `minimum version check failed` | rtcd build older than plugin's `min_rtcd_version` | Upgrade rtcd image / binary |
| Clients stuck "connecting" / no media | UDP 8443 blocked, or `ice_host_override` not set behind NAT | Open the port; set the override |
| `bind: address already in use` on startup | Another process on `:8045` or `:8443` | Pick different ports, or stop the conflicting service |
| All TURN-relayed media fails | Mismatched `turn.static_auth_secret` between rtcd and TURN server | Align both sides |
| Repeated `failed to write to UDP socket: too many open files` | fd limit hit | Raise `LimitNOFILE` (systemd) or lower `udp_sockets_count` |
