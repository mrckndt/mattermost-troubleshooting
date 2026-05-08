### calls-offloader

**What**: Kubernetes / Docker-native job runner that offloads Calls `recorder` and `transcriber` workloads from app nodes
**Stack**: Go backend, container orchestration via Docker or Kubernetes, SQLite store (or external DB)
**Min server**: Mattermost 7.6+ (Enterprise) with `mattermost-plugin-calls`

**Pipeline reference**: end-to-end recording flow + cross-component version matrix in `claude-md/mattermost-plugin-calls.md > Calls pipeline reference`.

**Configuration (key fields)**:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `api.http.listen_address` | String | `:4545` | API bind address |
| `jobs.api_type` | Enum | `docker` | Executor: `docker` or `kubernetes` |
| `jobs.max_concurrent_jobs` | Integer | `2` (in `SetDefaults` and `config.sample.toml`) | Max parallel runners. The doc-recommended starting value for production deployments (per `calls-offloader-setup.md`) is `100`; tickets reporting "max concurrent jobs reached" usually trace back to leaving the default `2`. |
| `jobs.image_registry` | String | `mattermost` | Docker registry prefix |
| `jobs.failed_jobs_retention_time` | Duration | `30d` | Retention for failed jobs; `0` = forever |
| `store.data_source` | String | `/tmp/calls-offloader-db` | SQLite path or external DB DSN |
| `jobs.kubernetes.persistent_volume_claim_name` | String | - | PVC for recording storage |
| `jobs.kubernetes.node_sysctls` | String | - | Node sysctls (e.g. `kernel.unprivileged_userns_clone=1`) |

**Network requirements**:

| Service | Port | Protocol | Notes |
|---|---|---|---|
| Offloader API | 4545 | TCP/HTTP(S) | Calls plugin -> offloader |
| Job pod <-> Mattermost | (varies) | TCP/HTTP | Jobs must reach the Calls plugin for status / uploads |
| K8s API | 6443 | TCP | When `api_type=kubernetes` |

- Self-registration (`allow_self_registration=true`) is safe only on internal networks; default off. The doc-recommended setup script enables it (per `calls-offloader-setup.md`) since the API port is restricted to the Mattermost subnet.
- For private-network deployments, set `MM_CALLS_RECORDER_SITE_URL` / `MM_CALLS_TRANSCRIBER_SITE_URL` **on the Mattermost server** (not the offloader) so spawned recorder / transcriber jobs use an internal URL to reach Mattermost. Per the doc, this also lets jobs use HTTP instead of HTTPS - acceptable inside a private network only. May require expanding `ServiceSettings.AllowCorsFrom` so CORS doesn't block the requests.
- Docker mode requires the offloader user to have access to the Docker daemon socket (`sudo usermod -a -G docker calls-offloader` per `calls-offloader-setup.md`).
- `calls-offloader-setup.md` "Storage Requirements" capacity guidance (call recordings, screen sharing on, one audio track): **Low** ~0.5GB/h (~8MB/min), **Medium** ~0.7GB/h (~12MB/min), **High** ~1.2GB/h (~20MB/min). Audio-only recordings ~1MB per minute per participant.

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Main config loading | `cmd/offloader/main.go` |
| Service config struct | `service/config.go` |
| K8s job scheduling | `service/kubernetes/service.go` |
| Docker job execution | `service/docker/service.go` |
| Job validation (versions, runners) | `public/job/job.go` |
| Auth and registration | `service/auth/` |

### Common Investigation Patterns

**Authoritative customer-facing docs**: `https://docs.mattermost.com/administration-guide/configure/calls-offloader-setup.html` (incl. air-gapped install). Cite the published URL in customer replies. Local source: `upstream/docs/source/administration-guide/configure/calls-offloader-setup.md`.

**Air-gapped install**: Per `calls-offloader-setup.md`, two-phase workflow using community scripts at `https://github.com/bgardner8008/calls-install-scripts`: (1) on an internet-connected host, `setup-airgap-offloader.sh` pulls recorder + transcriber Docker images and the offloader binary into a transfer bundle; (2) on the air-gapped host, `deploy-airgap-offloader.sh` loads the images into a local registry, installs the binary to `/usr/local/bin/`, creates the `mattermost` user, generates a systemd unit, and starts the service. For very restrictive K8s/VM isolation, set `DOCKER_NETWORK=host` so job containers can reach the Mattermost server via its local address. To use an existing internal Docker registry, run `install-offloader.sh --image-registry registry.internal.example.com/mattermost` instead of the local-registry path.

**Quick connectivity verification** (per `calls-offloader-setup.md`):

```
# From the offloader host:
curl http://localhost:4545/version
# Expected: {"buildDate":"...","buildVersion":"vX.Y.Z","buildHash":"...","goVersion":"..."}

# From the Mattermost server (confirms Mattermost -> offloader 4545 path):
curl http://YOUR_OFFLOADER_SERVER:4545/version

# Verify the offloader user can use Docker (Docker mode):
sudo -u calls-offloader docker ps
```

If localhost works but the cross-host check fails: firewall / SELinux on 4545, or no network path from Mattermost subnet to the offloader host.

**Jobs fail to start or time out**: Confirm `JOBS_APITYPE` matches the deployment mode. K8s: verify `K8S_NAMESPACE` env var, ServiceAccount has RBAC for `batch/jobs` and `pods/logs`. Docker: ensure the daemon is running and the offloader process is in the `docker` group. Inspect running job containers with `docker ps --format '{{.ID}} {{.Image}}' | grep calls`; tail with `docker logs -f <id>` (recipe from `calls-offloader-setup.md` Debugging Commands).

**Container image pull failures**: Verify `JOBS_IMAGEREGISTRY` (default `mattermost`) is reachable from the job runtime. Image tags must satisfy the minimum runner versions: `calls-recorder >= 0.6.0`, `calls-transcriber >= 0.1.0`. K8s: add `imagePullSecrets` for a private registry.

**Jobs cannot reach Mattermost (callback failures)**: Verify the Calls plugin URL is reachable from the job pod / container. K8s: check NetworkPolicy, DNS, and firewall. For private networks, set `MM_CALLS_RECORDER_SITE_URL` on the Calls plugin to a URL reachable from the runner. Inspect job pod logs (`kubectl logs <job-pod>`).

### Calls-Offloader Errors

| Error | Cause | Check |
|---|---|---|
| `invalid APIType value` | Unsupported job API in config | Use `docker` or `kubernetes` |
| `invalid empty Runners` | No runners configured | Set `runners` in job config or plugin settings |
| `failed to validate runner "..."` | Runner image invalid or version too low | Ensure image is `<registry>/calls-{recorder\|transcriber}:vX.Y.Z` and version meets the minimum |
| `authentication failed` | Calls plugin credentials don't match | Verify client ID / auth key in Mattermost env vars |
| `ImagePullBackOff` (K8s) | Container image unreachable | Check registry credentials, network policy |
| `CrashLoopBackOff` (K8s) | Pod fails repeatedly | Inspect pod logs and init-container sysctls |
