### enterprise (private)

#### LDAP sync silently skips a returning user

AD/LDAP sync matches users to LDAP entries strictly by `Users.AuthData` (the configured `IdAttribute`, e.g. `uidNumber`),
with no email/username fallback. If an LDAP entry is recreated with a different `IdAttribute`, the stored `AuthData` no
longer matches and sync skips that row, leaving `DeleteAt != 0`. Logs show the LDAP fetch as "foreign user" but not the
existing row.

**Diagnosis:** compare `Users.AuthData` to the LDAP `IdAttribute` (query via `ldapsearch` with the configured `BindDN`,
`BaseDN`, `UserFilter`, `LoginIdAttribute`). For more detail, enable LDAP trace logging in `LogSettings.AdvancedLoggingJSON`
(levels `LDAPTrace=144` through `LDAPError=140`) and disable it afterwards.

**Fix:** back up, then run `UPDATE Users SET AuthData = '<current-ldap-id>' WHERE Id = '<user-id>'` and
**System Console > Authentication > AD/LDAP > AD/LDAP Synchronize Now**. This reactivates the user.

#### Switching a user's auth method via the database

Used for maintenance (migrating between providers, realigning auth with external IdPs) or last-resort recovery when
System Console is unavailable. Back up first, then update both `users` columns consistently:

- **`authservice`:** one of `saml`, `ldap`, `gitlab`, `office365`, `google`, `openid`, or `''` (empty string, not NULL)
  for email/password.
- **`authdata`:** the user's `IdAttribute` from the provider (must be unique) for SSO/LDAP; `NULL` (not empty string)
  for email/password.

For conflicting/duplicate SAML `AuthData`, prefer `mmctl`:

```
mmctl saml auth-data-reset --users <user_id_1>,<user_id_2> --include-deleted
```

Takes user IDs only (resolve via `mmctl user search <username>`). `--include-deleted` also resets deactivated rows with
conflicting `AuthData`. The next SAML login repopulates `AuthData` from the configured `IdAttribute`.

**Signature this resolves:** SAML login warns `Unable to update existing SAML user. Allowing login anyway.` followed by
`Error 1062: Duplicate entry '<username>' for key 'Users.Username'` (from duplicate provisioning, IdP ID changes, or
prior manual DB edits).

#### OAuth/SSO callback fails with HTTP 414

**Symptom:** `URL is too long` / HTTP 414 during the IdP callback (e.g. `/signup/<provider>/complete?...`). The request is
rejected before the OAuth handler, so logs show no `completeOAuth` entry. Common with Microsoft Entra ID (large
`code`/`state` parameters), possible with any provider.

**Cause:** `ServiceSettings.MaximumURLLength` (default 2048) caps request URL length.

**Fix:** rule out the reverse proxy first (NGINX `large_client_header_buffers`, etc.), then raise
`ServiceSettings.MaximumURLLength` in `config.json` to the minimum value that resolves the issue (4096, or 8192 if
needed) and restart.

#### Cluster gossip drop: `sendto: message too long`

**Symptom:** cluster nodes log `sendto: message too long` on UDP gossip. Production instances show `buf_len` of
98-357 KB, well above the ~65 KB ceiling.

**Cause:** the gossip transport is UDP with a ~65 KB payload ceiling; any larger `ClusterMessage` is silently dropped.
Two common sources:

- Large `omit_users` broadcast lists.
- Plugins generating oversized DM posts that inflate WebSocket events. The GitHub plugin was a confirmed source (fixed,
  see `mattermost-plugin-github` notes).

**Diagnosis (v11.7.0+):** `model.ClusterMessage.LogFields()` (PR #36214) logs event-specific context on cluster errors.
For WebSocket broadcast events (`ClusterEventPublish`):

```
msg="sendto: message too long" ws_event=<type> channel_id=<id> team_id=<id> omit_users_len=<n>
```

For plugin events (`ClusterEventPluginEvent`):

```
msg="sendto: message too long" plugin_id=<id> event_id=<id>
```

A large `omit_users_len` indicates broadcast fan-out; a `plugin_id` identifies the offending plugin.

**Diagnosis (before v11.7.0):** only `event: publish` is logged. Use `tcpdump` on the gossip port
(`ClusterSettings.GossipPort`, default 8074) to inspect payload sizes.

#### AWS OpenSearch bulk index only covers one day (v9.11+)

**Symptom:** bulk index succeeds but only indexes today's posts; historical data is missing. Purge Indexes fails
silently. Logs show `flush: 404 page not found`.

**Cause:** AWS OpenSearch blocks wildcard destructive operations and doesn't allow setting `action.destructive_requires_name=false`.
Purges on system indices fail silently, leaving stale state that breaks reindexing.

**Fix:**

1. Set **System Console > Environment > Elasticsearch > Indexes to skip while purging** to
   `.plugins-*,.kibana*,.opendistro*,.opensearch*,.ql-*,.tasks*` (skips AWS-managed system indices).
2. Toggle Elasticsearch indexing off, then on again.
3. Run **Purge Indexes**, then **Index Now**.
4. If stale indexing jobs remain, back up and clear them:

   ```
   DELETE FROM Jobs WHERE Type = 'elasticsearch_post_indexing';
   ```

5. Re-trigger Bulk Indexing. If still problematic, inspect templates:
   `curl -X GET <OPENSEARCH_URL>/_index_template -u USER:PASS`.
