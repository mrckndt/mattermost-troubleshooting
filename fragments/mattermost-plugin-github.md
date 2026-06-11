### mattermost-plugin-github

#### Oversized DM posts causing cluster gossip drops

Webhook notifications with large diffs could exceed the ~65 KB UDP gossip limit, causing silent drops. Fixed in PR #1003 (May 6): `CreateBotDMPost` truncates bodies at `model.PostMessageMaxRunesV2`, preserving UTF-8 boundaries and appending `… message truncated`. Users seeing truncations should check GitHub directly.
