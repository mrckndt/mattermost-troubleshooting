### mattermost-operator

**What**: Kubernetes Operator for deploying and managing Mattermost
**Stack**: Go, Operator SDK, controller-runtime
**CRDs**: `Mattermost` (v1beta1), `MattermostRestoreDB` (backup restore)

**CRD**: API group `installation.mattermost.com/v1beta1`, Kind `Mattermost`. Size presets: `100users`, `1000users`, `5000users` (default), `10000users`, `250000users`.
Size is write-only: it sets replicas/resources then clears itself. Manual overrides for `Replicas`, `Scheduling.Resources` take precedence over Size.

**Database configuration**:
- External: Kubernetes Secret (via `.spec.database.external.secret`) with `DB_CONNECTION_STRING` key, optional `MM_SQLSETTINGS_DATASOURCEREPLICAS`, `DB_CONNECTION_CHECK_URL`
- Operator-managed: provisions via MySQL operator

**File storage options**: external S3/MinIO (`.spec.fileStore.external`), operator-managed MinIO (`.spec.fileStore.operatorManaged`), local PVC (`.spec.fileStore.local`, not for production), external volume (`.spec.fileStore.externalVolume`)

**ElasticSearch**: configured via `host`, `username`, `password` fields in CRD spec

**Auto-set environment variables** (always applied, cannot be overridden via `mattermostEnv`):
- `MM_CLUSTERSETTINGS_ENABLE=true`
- `MM_METRICSSETTINGS_ENABLE=true`
- `MM_METRICSSETTINGS_LISTENADDRESS=:8067`
- `MM_CLUSTERSETTINGS_CLUSTERNAME=production`
- `MM_PLUGINSETTINGS_ENABLEUPLOADS=true`
- `MM_INSTALL_TYPE=kubernetes-operator`

**Backup/Restore**: `MattermostRestoreDB` CRD supports Percona XtraBackup restoration from S3. Requires `initBucketURL` and `restoreSecret` in restore spec.

**Key paths**:

| Area | Path |
|---|---|
| CRD type definitions | `apis/mattermost/v1beta1/mattermost_types.go` |
| Legacy CRD (ClusterInstallation) | `apis/mattermost/v1alpha1/` |
| Environment variable logic | `pkg/mattermost/env_var.go` |
| CRD documentation | `docs/mattermost_v1beta1_crd.md` |
| Migration guide (v1alpha1 to v1beta1) | `docs/migration.md` |
| Sample CRs | `config/samples/` |
