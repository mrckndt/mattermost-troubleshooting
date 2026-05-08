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
| `jobs.max_concurrent_jobs` | Integer | `2` | Max parallel runners |
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

- Self-registration (`allow_self_registration=true`) is safe only on internal networks; default off.
- For private-network deployments, set `MM_CALLS_RECORDER_SITE_URL` / `MM_CALLS_TRANSCRIBER_SITE_URL` on the Calls plugin to override URLs the runners use to call back.
- Docker mode requires the offloader user to have access to the Docker daemon socket.

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

**Jobs fail to start or time out**: Confirm `JOBS_APITYPE` matches the deployment mode. K8s: verify `K8S_NAMESPACE` env var, ServiceAccount has RBAC for `batch/jobs` and `pods/logs`. Docker: ensure the daemon is running and the offloader process is in the `docker` group.

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
