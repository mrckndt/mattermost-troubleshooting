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
- Default MySQL credentials: user `mmuser`, password `passwd`, root password `rootpasswd` - MUST be changed for production. Defined in `charts/mattermost-enterprise-edition/values.yaml`.
- Default MinIO credentials: `mattermostadmin`/`mattermostadmin` - MUST be changed for production. Defined in `charts/mattermost-enterprise-edition/values.yaml`.

**Helm-chart-specific pitfalls** (generic K8s deployment pitfalls live in CLAUDE.md "Deployment pitfalls"):
- Ingress enabled without a TLS secret configured.
- Cluster communication ports (gossip 8074, streaming 8075) blocked by NetworkPolicy.
- PVC default size (10Gi) may be insufficient for production workloads.

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

### Common Investigation Patterns

**Ingress drops WebSocket**: NGINX ingress and many cloud LBs need explicit annotations to forward `Upgrade` / `Connection` headers and an idle timeout >60s. Without that, `/api/v4/websocket` connections die after the proxy's default idle timeout. Verify `nginx.ingress.kubernetes.io/proxy-read-timeout` >= 3600.

**StatefulSet PVC stuck pending**: Pod can't start. Usually a `StorageClass` mismatch or no provisioner. `kubectl describe pvc <name>` should show the binding error. For local-path tests, set `global.features.fileStore.driver=local` (NOT for production - breaks HA).

**Cluster gossip blocked**: Pods can't form a cluster. Network policies must allow gossip 8074 and streaming 8075 between Mattermost pods. The chart adds `clusterPort`/`gossipPort` Service entries; confirm they aren't filtered upstream of the Service.

**Pod crash-loop triage**:
```
kubectl describe deployment mattermost-<release> -n <namespace>  # Events: image pull, quota, missing secrets
kubectl logs -l app=mattermost -n <namespace> --previous --tail=100  # DB errors, migration failures
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -20
```

**`mattermostApp.extraEnv` vs `mattermostApp.service.annotations`**: `extraEnv` injects custom environment variables into the Mattermost pod (these become `MM_*` overrides). `service.annotations` controls the Kubernetes Service object (NLB annotations, Prometheus scraping). Common mistake: putting `nginx.ingress.kubernetes.io/*` annotations in `extraEnv` - they have no effect there; they belong in `ingress.annotations`.
