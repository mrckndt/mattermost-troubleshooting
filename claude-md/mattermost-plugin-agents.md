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

**Key paths**: `config/config.go` (configuration), `llm/` (LLM integration), `mcp/` (MCP tools), `docs/admin_guide.md` (admin setup guide)
