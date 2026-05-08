### mattermost-plugin-agents

**What**: AI agents plugin with LLM integration and MCP tools
**Stack**: Go backend, React/TypeScript frontend
**Plugin ID**: `mattermost-ai`
**Min server**: 6.2.1
**Database**: PostgreSQL (requires pgvector extension for semantic search)

**Supported LLM providers**: OpenAI, Anthropic (Claude), AWS Bedrock, Cohere, Mistral, Scale AI, Azure OpenAI, Google Gemini, Google Vertex, OpenAI-compatible (Ollama, vLLM, local models)

**Embedded MCP tools** (14 non-dev): `create_post`, `read_post`, `dm`, `group_message`, `read_channel`, `create_channel`, `get_channel_info`, `get_channel_members`, `add_user_to_channel`, `get_user_channels`, `get_team_info`, `get_team_members`, `search_posts`, `search_users`. Additional dev-mode tools: `create_post_as_user`, `create_team`, `add_user_to_team`, `create_user`.

**Key config**:
- `EnableLLMTrace`: debug logging for LLM calls
- `EnableTokenUsageLogging`: track token usage
- `AllowedUpstreamHostnames`: API allowlist for outbound calls
- `AllowUnsafeLinks`: security setting for rendered links
- `EmbeddingSearchConfig`: semantic search (requires pgvector)
- `MCP.enabled`: Model Context Protocol tool-calling. Full `MCPConfig` also has `enablePluginServer`, `servers`, `embeddedServer`, `idleTimeoutMinutes` (`config/mcp_config.go`).
- SiteURL must be correctly configured for MCP server to work

**Key paths for troubleshooting**:

| Area | Path |
|---|---|
| Configuration | `config/config.go` |
| MCP config | `config/mcp_config.go` |
| LLM provider integration | `llm/` |
| MCP tools (server-side) | `mcpserver/tools/` |
| MCP server / client | `mcp/` |
| Admin setup guide | `docs/admin_guide.md` |

### Common Investigation Patterns

**pgvector extension missing**: Semantic search / embeddings disabled or fail with `extension "vector" does not exist`. The DB admin must `CREATE EXTENSION vector;` on the Mattermost database. Without pgvector, configure `EmbeddingSearchConfig` to disable embeddings or fall back to a non-semantic retriever.

**MCP server unreachable**: see "Operational checks" below for endpoint paths and probe. Two separate toggles (embedded vs external HTTP); SiteURL must be reachable from where the LLM client runs.

**Model config mismatch**: LLM provider returns 4xx/5xx. Check `EnableLLMTrace=true` to log the request/response. Common causes: wrong endpoint URL for OpenAI-compatible servers (Ollama uses `/v1`), missing `AllowedUpstreamHostnames` entry blocking outbound calls, or token-limit mismatch (provider rejects context-length overrun).

### Operational checks

**pgvector audit** (semantic search requires the `vector` extension on the Mattermost database):

```
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

If empty: have the DB admin run `CREATE EXTENSION vector;` on the Mattermost database (requires superuser unless pre-allowlisted on the cloud DB provider). Without it, configure `EmbeddingSearchConfig` to disable embeddings or use **Post indexing** (System Console > Plugins > Agents > Embedding Search) only after the extension is in place.

**MCP server reachability** (external client like Claude Code/Desktop cannot connect):

The plugin exposes two MCP endpoints with separate enable toggles in **System Console > Plugins > Agents > MCP Servers**:

| Mode | Toggle | Endpoint | Used by |
|---|---|---|---|
| Embedded | `Enable Embedded Server` | internal only | the plugin's own AI agents |
| External | `Enable Mattermost MCP Server (HTTP)` | `https://<SiteURL>/plugins/mattermost-ai/mcp-server/mcp` | Claude Code, Claude Desktop, other MCP clients |

External-client probe (PAT in `User Settings > Security > Personal Access Tokens`, or use OAuth):

```
curl -i -H "Authorization: Bearer <PAT>" \
  https://<SiteURL>/plugins/mattermost-ai/mcp-server/mcp
```

Transport is **streamable HTTP only** - the server does not implement SSE; clients configured for SSE will fail to connect. SiteURL must be reachable from wherever the LLM client runs, not just from inside the cluster. OAuth metadata: `/plugins/mattermost-ai/mcp-server/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server`.

**License**: MCP support requires Entry, Enterprise, or Enterprise Advanced.
