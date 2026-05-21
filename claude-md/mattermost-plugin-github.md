### mattermost-plugin-github

#### Oversized DM posts causing cluster gossip drops

Webhook notifications with large diffs could produce DM post bodies exceeding the cluster UDP gossip limit (~65 KB), causing silent message drops across nodes. Fixed in `https://github.com/mattermost/mattermost-plugin-github/commit/18a5bfcdb05b69aa35e95e5cbd25e23f9fadb085` (PR #1003, merged May 6): `CreateBotDMPost` now truncates bodies at `model.PostMessageMaxRunesV2`, preserving UTF-8 boundaries and appending a `… message truncated` marker. Users seeing truncated notifications should check GitHub directly for full content.
