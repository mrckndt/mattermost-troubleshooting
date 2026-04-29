### enterprise (private)

**What**: Source-available implementation of Mattermost enterprise features (LDAP, SAML, clustering, compliance, data retention, message export, ABAC, auto-translation, OAuth providers, etc.). Compiled into the server binary via build tags; community edition omits this code entirely.
**Stack**: Go
**License gating**: Every feature checks `License().Features.<FeatureName>` before operating. Tiers: E10, E20, Professional, Enterprise, Enterprise Advanced, Mattermost Entry.
**Database**: cross-ref `mattermost.md`.

This is a **private** repo. If `upstream/enterprise/` is missing, the user does not have access; fall back to OSS-only reasoning and surface the gap.

**Integration model**:
- Interfaces are defined in the OSS server: `upstream/mattermost/server/einterfaces/`.
- Implementations register themselves via `init()` calls into `upstream/mattermost/server/channels/app/enterprise.go` (`Register{Feature}Interface()`).
- Build tags route the imports: `//go:build enterprise` for private code, `//go:build enterprise || sourceavailable` for source-available code.

**Key paths (per feature package)**:

| Feature | Path | Implements (interfaces in OSS `einterfaces/`) | License feature flag |
|---|---|---|---|
| LDAP / AD | `ldap/` | `LdapInterface`, `LdapDiagnosticInterface`, `ejobs.LdapSyncInterface` | `Features.LDAP`, `Features.LDAPGroups` |
| SAML 2.0 | `saml/` | `SamlInterface` | `Features.SAML` |
| Clustering | `cluster/` | `ClusterInterface` | `Features.Cluster` |
| Compliance | `compliance/` | `ComplianceInterface` | `Features.Compliance` |
| Data retention | `data_retention/` | `DataRetentionInterface`, `ejobs.DataRetentionJobInterface` | `Features.DataRetention` |
| Message export | `message_export/` | `MessageExportInterface`, `ejobs.MessageExportJobInterface` | `Features.MessageExport`, `Features.Compliance` |
| Cloud / CWS | `cloud/` | `CloudInterface` | Cloud-specific |
| Access control (ABAC) | `access_control/` | `AccessControlServiceInterface`, `ejobs.AccessControlSyncJobInterface` | Enterprise Advanced; flag `AttributeBasedAccessControl` |
| Auto-translation | `autotranslation/` | `AutoTranslationInterface` | `MinimumEnterpriseAdvancedLicense` |
| Account migration | `account_migration/` | `AccountMigrationInterface` | - |
| Push proxy | `push_proxy/` | `PushProxyInterface` | - |
| Notification (ID-loaded) | `notification/` | `NotificationInterface` | - |
| Intune (MAM) | `intune/` | `IntuneInterface` | License-tier check via `model.MinimumEnterpriseAdvancedLicense(license)` (not a `Features` flag); also requires O365 or SAML enabled |
| IP filtering (cloud) | `ip_filtering/` | `IPFilteringInterface` | Cloud-only |
| OAuth (Google/O365/OIDC) | `oauth/{google,office365,openid}/` | (provider-specific) | - |
| Outgoing OAuth | `outgoing_oauth_connections/` | `OutgoingOAuthConnectionInterface` | `Features.OutgoingOAuthConnections` |
| License | `license/` | `LicenseInterface` | - |

**Enterprise-specific config knobs** (tunable by admins; defined in OSS config struct, used by enterprise impl):

- **LDAP**: `LdapSettings.EnableSync`, `LdapSettings.SyncIntervalMinutes` (0 disables periodic sync), `LdapSettings.QueryTimeout`.
- **Data retention**: `DataRetentionSettings.EnableMessageDeletion`, `EnableFileDeletion`, `BatchSize`, `TimeBetweenBatchesMilliseconds`.
- **Message export**: `MessageExportSettings.BatchSize`, `ChannelBatchSize`, `ChannelHistoryBatchSize`.
- **Compliance**: `ComplianceSettings.BatchSize`.
- **Outgoing OAuth**: `ServiceSettings.EnableOutgoingOAuthConnections`.
- **Auto-translation**: 10-minute cache TTL (default).
- **TURN credentials** (cluster, when used): expire in 240 minutes (configurable; not enterprise-specific - see calls plugin).

If a feature appears disabled despite a valid license, these are usually the next things to check after the license + feature-flag pair.

**SAML extra**: `xmlsec1` system binary required for testing SAML signing/encryption.

**Clustering implementation notes**:
- Inter-node messaging: gossip protocol via memberlist (`cluster/gossip_client.go` + per-feature handlers).
- Redis fallback: `cluster/redis.go` for broadcast.
- Leader election, config/log/plugin-status sync, support-packet collection across all nodes.

**Auto-translation providers**: `provider/libretranslate/`, `provider/agents/` (uses the Mattermost Agents AI plugin). 10-minute TTL cache, sensitive-data masking, recovery job for failures.

**Error message convention**:

Enterprise translation IDs are prefixed with `ent.` in `upstream/mattermost/server/i18n/en.json`. Examples seen in code:
- `ent.saml.license_disable.app_error`
- `ent.data_retention.generic.license.error`
- `ent.data_retention.policies.invalid_policy`
- `ent.autotranslation.feature_unavailable`
- `ent.outgoing_oauth_connections.license_disable.app_error`
- `ent.outgoing_oauth_connections.feature_disabled`
- `ent.access_control.sync_job.app_error`

Common error helpers (e.g., in `data_retention/data_retention.go`):
- `newLicenseError()` returns an error when the license doesn't include the feature.
- `newInternalError()` returns an internal server error with runtime caller info.

**License-checking pattern**: every enterprise feature validates its license before operating, by reading `Server.License()` and checking the relevant `Features.<Name>` flag (or a tier-min helper like `model.MinimumEnterpriseAdvancedLicense`). Grep for `License().Features.` across the OSS repo to find every gate.

### Common Support Investigation Patterns

**"Why is enterprise feature X not working?"**
1. License: does it include the feature? Check `Features` struct in `upstream/mattermost/server/public/model/license.go`.
2. Config: is the feature enabled in the relevant settings struct in `upstream/mattermost/server/public/model/config.go`?
3. Implementation-level validation: search the feature package here for `checkConfigAndLicense()` or similar (e.g., `saml/saml.go`).

**"What does error `ent.X.Y` mean?"**
1. Search `upstream/mattermost/server/i18n/en.json` for the ID to get the English text.
2. Grep this repo for the same ID to find where it's raised.
3. Read the surrounding code for the triggering condition.

**"How does clustering coordinate across nodes?"**
1. Entry point: `cluster/cluster.go`.
2. Gossip transport: `cluster/gossip_client.go` and per-feature handlers (`gossip_client_*.go`).
3. Redis broadcast alternative: `cluster/redis.go`.
4. Config: `ClusterSettings` in OSS config model.

**"LDAP group sync isn't running on schedule"**
1. `ldap/ldap_sync_scheduler.go` - schedule logic; honors `SyncIntervalMinutes` (0 disables).
2. `ldap/ldap_sync_job.go` - the worker. Look for last-run timestamp and error logs.
3. License gate: `Features.LDAPGroups` (separate from `Features.LDAP`).

**"Compliance / message export job stuck or producing partial output"**
1. Both use a scheduler + worker pattern via the OSS job system (`upstream/mattermost/server/channels/jobs/`).
2. Job definitions: `upstream/mattermost/server/public/model/job.go`.
3. Implementation: `compliance/` or `message_export/` here. `message_export/` has multiple format subdirs (`csv_export/`, `actiance_export/`, `global_relay_export/`) and SFTP/SMTP delivery.

**"AD attribute mapping not picking up custom attributes"**
1. `ldap/ldap.go` - sync logic and attribute mapping.
2. Custom profile attribute mapping is honored if defined; check the LDAP config block in OSS config (`LdapSettings`).
3. Diagnostic helper: `ldap/diagnostic.go` exposes the test endpoints.
