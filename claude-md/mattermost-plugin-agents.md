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

**MCP server unreachable from agent**: SiteURL must be set correctly - the embedded MCP server is reached via `{SiteURL}/plugins/mattermost-ai/mcp`. If the LLM client (Claude Code / Claude Desktop) can't reach it, verify SiteURL is publicly accessible from where the LLM runs, not just from inside the cluster.

**Model config mismatch**: LLM provider returns 4xx/5xx. Check `EnableLLMTrace=true` to log the request/response. Common causes: wrong endpoint URL for OpenAI-compatible servers (Ollama uses `/v1`), missing `AllowedUpstreamHostnames` entry blocking outbound calls, or token-limit mismatch (provider rejects context-length overrun).
