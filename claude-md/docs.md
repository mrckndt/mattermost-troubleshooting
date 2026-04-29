### docs (product documentation)

**What**: Official Mattermost product documentation source (generates docs.mattermost.com)
**Stack**: Sphinx (reStructuredText), Python
**Format**: RST files under `source/`

This is the primary reference for all admin, deployment, and configuration documentation. When answering support questions, search this repo for authoritative guidance before making claims about product behavior.

**Key content areas and paths** (all under `source/`):

| Topic | Path |
|---|---|
| **All configuration settings** | `administration-guide/configure/configuration-settings.rst` |
| Environment config settings | `administration-guide/configure/environment-configuration-settings.rst` |
| Auth config settings | `administration-guide/configure/authentication-configuration-settings.rst` |
| Environment variables | `administration-guide/configure/environment-variables.rst` |
| Database-backed config | `administration-guide/configure/configuration-in-your-database.rst` |
| Push notification config | `administration-guide/configure/push-notification-server-configuration-settings.rst` |
| Plugin config settings | `administration-guide/configure/plugins-configuration-settings.rst` |
| Calls overview | `administration-guide/configure/calls-overview.rst` |
| **LDAP/AD integration** | `administration-guide/onboard/ad-ldap.rst` |
| LDAP group sync | `administration-guide/onboard/ad-ldap-groups-synchronization.rst` |
| **SAML SSO** (multiple providers) | `administration-guide/onboard/sso-saml-*.rst` |
| OpenID Connect SSO | `administration-guide/onboard/sso-openidconnect.rst` |
| Certificate-based auth | `administration-guide/onboard/certificate-based-authentication.rst` |
| **High availability / clustering** | `administration-guide/scale/high-availability-cluster-based-deployment.rst` |
| Elasticsearch setup | `administration-guide/scale/elasticsearch-setup.rst` |
| OpenSearch setup | `administration-guide/scale/opensearch-setup.rst` |
| Prometheus/Grafana monitoring | `administration-guide/scale/deploy-prometheus-grafana-for-performance-monitoring.rst` |
| Performance metrics reference | `administration-guide/scale/performance-monitoring-metrics.rst` |
| Scaling guides (200 to 200K users) | `administration-guide/scale/scale-to-*-users.rst` |
| Push notification health | `administration-guide/scale/push-notification-health-targets.rst` |
| **Upgrade guide** | `administration-guide/upgrade/upgrading-mattermost-server.rst` |
| Important upgrade notes | `administration-guide/upgrade/important-upgrade-notes.rst` |
| Upgrade prep checklist | `administration-guide/upgrade/prepare-to-upgrade-mattermost.rst` |
| K8s HA upgrade | `administration-guide/upgrade/upgrade-mattermost-kubernetes-ha.rst` |
| **mmctl CLI reference** | `administration-guide/manage/mmctl-command-line-tool.rst` |
| Logging reference | `administration-guide/manage/logging.rst` |
| Support packet generation | `administration-guide/manage/admin/generating-support-packet.rst` |
| Health check probes | `administration-guide/manage/configure-health-check-probes.rst` |
| Data retention policy | `administration-guide/comply/data-retention-policy.rst` |
| Compliance export | `administration-guide/comply/compliance-export.rst` |
| Audit log schema | `administration-guide/comply/embedded-json-audit-log-schema.rst` |
| **Deployment troubleshooting** | `deployment-guide/deployment-troubleshooting.rst` |
| Server troubleshooting | `deployment-guide/server/troubleshooting.rst` |
| Docker troubleshooting | `deployment-guide/server/docker-troubleshooting.rst` |
| PostgreSQL troubleshooting | `deployment-guide/server/trouble-postgres.rst` |
| Desktop troubleshooting | `deployment-guide/desktop/desktop-troubleshooting.rst` |
| Mobile troubleshooting | `deployment-guide/mobile/mobile-troubleshooting.rst` |
| PostgreSQL migration | `deployment-guide/postgres-migration.rst` |
| TLS/SSL setup | `deployment-guide/server/setup-tls.rst` |
| Encryption options | `deployment-guide/encryption-options.rst` |
| Linux deploy (Ubuntu) | `deployment-guide/server/linux/deploy-ubuntu.rst` |
| Linux deploy (RHEL) | `deployment-guide/server/linux/deploy-rhel.rst` |
| Docker deploy | `deployment-guide/server/deploy-containers.rst` |
| Kubernetes deploy | `deployment-guide/server/deploy-kubernetes.rst` |
| Server deployment planning | `deployment-guide/server/server-deployment-planning.rst` |
