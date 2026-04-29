### mattermost-helm

**What**: Official Helm charts for deploying Mattermost and related services in Kubernetes
**Stack**: Helm 3, Kubernetes manifests (YAML templates)

**Charts** (in `charts/` directory):

| Chart | Status |
|---|---|
| `mattermost-operator` | Recommended for new deployments |
| `mattermost` | Standalone (no operator) |
| `mattermost-enterprise-edition` | Legacy, no longer supported |
| `mattermost-rtcd` | RTCD for Calls plugin |
| `mattermost-push-proxy` | Push notification proxy |
| `mattermost-calls-offloader` | Calls recording/transcription offloader |

**mattermost-operator chart** (recommended):
- Deploys the Kubernetes Operator that manages Mattermost installations via CRD
- Key values: `mattermostOperator.enabled`, `mattermostOperator.replicas`, `mattermostOperator.image.tag`
- Operator handles lifecycle: create, update, scale, backup
- See the `mattermost-operator` repo section above for CRD details

**mattermost chart** (standalone, no operator):
- Key values: `global.siteUrl` (required), `global.features.database.driver` (default `postgres`), `global.features.database.dataSource` (required), `global.features.fileStore.driver` (default `amazons3`)
- Cluster ports: `clusterPort` (8075), `gossipPort` (8074)
- Default replicas: 2
- Supports HPA autoscaling

**mattermost-enterprise-edition chart** (legacy):
- Key values: `global.siteUrl` (required), `global.mattermostLicense` (required)
- Subcharts: `mysqlha`, `minio`, `prometheus` (all conditional)
- Default MySQL credentials: user `mmuser`, password `passwd`, root password `rootpasswd` - MUST be changed for production
- Default MinIO credentials: `mattermostadmin`/`mattermostadmin` - MUST be changed for production

**Common pitfalls**:
- Not setting required fields: `global.siteUrl`, license, database connection string
- Using default MySQL/MinIO passwords in production
- Using local file storage driver instead of S3/MinIO in production (breaks HA)
- Ingress enabled without TLS secret configured
- Missing cluster communication ports (gossip 8074, cluster 8075) in network policies
- PVC default size (10Gi) may be insufficient for production workloads

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Operator chart values | `charts/mattermost-operator/values.yaml` |
| Operator chart templates | `charts/mattermost-operator/templates/` |
| Standalone chart values | `charts/mattermost/values.yaml` |
| Standalone chart templates | `charts/mattermost/templates/` |
| Legacy enterprise chart values | `charts/mattermost-enterprise-edition/values.yaml` |
| Legacy enterprise chart templates | `charts/mattermost-enterprise-edition/templates/` |
| RTCD chart | `charts/mattermost-rtcd/` |
| Push proxy chart | `charts/mattermost-push-proxy/` |
