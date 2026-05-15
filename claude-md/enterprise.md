### enterprise (private)

#### LDAP sync silently skips a returning user

AD/LDAP sync matches existing Mattermost users to LDAP entries strictly by `Users.AuthData` (= configured `IdAttribute`, e.g. `uidNumber`). No email/username fallback. If a returning user's LDAP entry was recreated with a different `IdAttribute` value than before, the stored `AuthData` no longer matches and the sync does nothing for that row, leaving `DeleteAt != 0`. The trace shows the LDAP-side fetch as a "foreign user" but no log line for the existing row.

Confirm by comparing `Users.AuthData` to the live LDAP `IdAttribute` value (via `ldapsearch` with the configured `BindDN`, `BaseDN`, `UserFilter`, `LoginIdAttribute`).

Fix: back up, then `UPDATE Users SET AuthData = '<current-ldap-id>' WHERE Id = '<user-id>'`, then **System Console > Authentication > AD/LDAP > AD/LDAP Synchronize Now**. The next sync reactivates the user automatically. For deeper diagnosis, enable LDAP trace logging via `LogSettings.AdvancedLoggingJSON` (levels `LDAPTrace=144` through `LDAPError=140`); disable after.

#### Switching a user's auth method via the database

Used for maintenance (e.g. migrating users between providers, realigning auth data with an external IdP) or last-resort recovery when System Console paths are unavailable. Always back up first. Update both columns on `users` consistently:

- `authservice`: provider. One of `saml`, `ldap`, `gitlab`, `office365`, `google`, `openid`, or `''` (empty string, not NULL) for email/password.
- `authdata`: external identifier. For SSO/LDAP, the user's `IdAttribute` value from the provider (must be unique across `users`). For email/password, `NULL` (not empty string).

For SAML specifically, prefer `mmctl` over a raw `UPDATE` when `AuthData` is conflicting/duplicated:

```
mmctl saml auth-data-reset --users <user_id_1>,<user_id_2> --include-deleted
```

Takes user IDs only (not usernames/emails); use `mmctl user search <username>` to resolve IDs. `--include-deleted` is required to also reset deactivated rows with conflicting `AuthData`. After reset, the next successful SAML login repopulates `AuthData` from the configured `IdAttribute`.

Signature this resolves: SAML login warns `Unable to update existing SAML user. Allowing login anyway.` followed by `Error 1062 (23000): Duplicate entry '<username>' for key 'Users.Username'`, typically from duplicate provisioning, an IdP-side ID change, or a prior manual DB edit that misassociated rows.

#### OAuth/SSO callback fails with HTTP 414

Symptom: `URL is too long` / HTTP 414 returned during the IdP callback (e.g. `/signup/<provider>/complete?...`). The request is rejected before reaching the OAuth handler, so server logs show no `completeOAuth` entry for the attempt. Common with Microsoft Entra ID due to large `code`/`state` parameters, but possible with any provider.

Cause: `ServiceSettings.MaximumURLLength` (default `2048`) caps incoming request URL length at the application layer. Rule out the reverse proxy first (NGINX `large_client_header_buffers`, etc.); if the proxy is fine, raise this setting to `4096` (or `8192` if needed) in `config.json` and restart. Pick the minimum value that resolves the issue.

#### AWS OpenSearch bulk index only covers one day (v9.11+)

Symptom: bulk index job reports success but only the current day's posts are indexed; historical data missing from search. Purge Indexes fails silently or partially. Server logs show `flush: 404 page not found`.

Cause: AWS OpenSearch (managed service) blocks the wildcard destructive operations Mattermost's purge relies on, and does not allow setting `action.destructive_requires_name=false`. The purge silently fails on AWS-protected system indices, leaving stale state that breaks the subsequent reindex.

Fix:

1. **System Console > Environment > Elasticsearch > Indexes to skip while purging**: `.plugins-*,.kibana*,.opendistro*,.opensearch*,.ql-*,.tasks*`. This avoids touching AWS-managed system indices.
2. Toggle Elasticsearch indexing off, then on again.
3. Run **Purge Indexes**, then **Index Now**.
4. If stale indexing jobs remain, clear them (back up first):

```
DELETE FROM Jobs WHERE Type = 'elasticsearch_post_indexing';
```

Then re-trigger Bulk Indexing. Inspect templates if still problematic: `curl -X GET <OPENSEARCH_URL>/_index_template -u USER:PASS`.
