# MCP Slack Bot - AI Coding Agent Instructions

## Project Overview

This is a **Slack bot that connects to MCP (Model Context Protocol) servers** to execute tools via LLM-powered natural language processing. Users mention the bot in Slack, and it intelligently routes queries to appropriate MCP tools or refuses non-tool queries.

**Key Architecture**: Single LLM decision point (intent analysis) → tool execution → result interpretation. NO multi-turn LLM conversations for general knowledge.

## Critical Architecture Decisions

### 1. Intent Analysis is the Single Source of Truth

The bot makes **ONE primary LLM call** (`ElicitationHandler.analyze_user_intent()`) that determines all subsequent actions:

- **OUTCOME 1**: `(tool_name, args, None)` → Execute tool immediately
- **OUTCOME 2**: `(tool_name, None, clarification_question)` → Ask user for missing parameters
- **OUTCOME 3**: `(None, None, None)` → **CONVERSATIONAL** query (no matching tool) → **REFUSE immediately**

**DO NOT** add logic to "answer" conversational queries after intent analysis returns `(None, None, None)`. The refusal message is generated dynamically in `SlackBot._generate_tool_capabilities_description()`.

See `utils/slackbot.py` lines 267-360 for the three outcomes with extensive inline documentation.

### 2. MCP Server Protocol Support

The bot supports **two MCP transport modes** (see `utils/server.py`):

- **stdio**: Subprocess-based servers (Docker, npx commands) - returns 2 values: `(read, write)`
- **HTTP**: HTTP-based MCP servers - returns 3 values: `(read, write, get_session_id)`

Check `self.is_http` to determine protocol. HTTP servers require graceful connection failure handling (see `SlackBot.start()` lines 89-98).

### 3. Tool Access Control via `allowedTools`

`servers_config.json` contains `allowedTools` array. Tools are filtered in:
- `Server.get_tools()` - creates `Tool` objects with `config` reference
- `Tool.is_allowed` property - checks if `tool.name` in `config.allowed_tools`

**NEVER execute tools where `tool.is_allowed == False`**. All lists must filter: `[tool for tool in tools if tool.is_allowed]`

### 4. Prompt Management through YAML

All LLM prompts live in `prompts/prompts_config.yaml`:
- **Intent analysis prompt**: The ONLY prompt controlling tool vs. conversational decision
- **Result interpretation prompts**: Server-specific customization for formatting tool outputs

Access via `PromptManager` methods. Server-specific overrides in `server_prompts` section (e.g., opensearch, binance, kafka).

## Development Workflows

### Running the Bot

```bash
# Setup (first time)
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Configure .env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
OPENAI_API_KEY=...
LLM_MODEL=llama3.2  # or gpt-4, gpt-3.5-turbo

# Run
python main.py
```

The bot validates:
1. Slack tokens present
2. MCP servers in `servers_config.json` exist
3. LLM connectivity (test call on startup - see `main.py` lines 74-84)
4. Graceful shutdown on SIGINT/SIGTERM

### Debugging Tool Matching

Enable debug logging to see intent analysis:
```python
logging.basicConfig(level=logging.DEBUG)
```

Look for these log markers in `utils/elicitation.py`:
- Line 83: `"INTENT ANALYSIS DEBUG"` - Shows query + tools sent to LLM
- Line 109: `"LLM RESPONSE FOR"` - Shows raw LLM response before parsing

### Adding New MCP Servers

1. Add to `servers_config.json`:
   ```json
   {
     "mcpServers": {
       "my_server": {
         "url": "http://localhost:8000/mcp"  // HTTP mode
         // OR
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-name"]
       }
     },
     "allowedTools": ["tool1", "tool2"]
   }
   ```

2. **Optional**: Add server-specific result interpretation prompts in `prompts/prompts_config.yaml` under `server_prompts.my_server`

3. Test startup - HTTP servers log warnings if unreachable (non-fatal)

## Code Conventions & Patterns

### Error Handling: Graceful Degradation

- **MCP server failures**: Log warning, continue with other servers (see `SlackBot.start()` lines 89-98)
- **Shutdown**: Suppress ALL exceptions in cleanup (`asyncio.CancelledError`, `Exception` - see `main.py` shutdown())
- **Tool execution**: Return user-friendly error strings, never raise to user (see `SlackBot.execute_tool()` line 413)

### Conversation Context: Per-User Keys

Conversations are keyed by `f"{channel}:{user}"` (see `SlackBot.process_message()` line 174), ensuring:
- Each user maintains separate history in the same channel
- Thread-based replies via `thread_ts` parameter
- History preserved for elicitation follow-ups

### LLM Integration: Dual Backend Support

`ChatBot` (in `utils/chatbot.py`) supports:
- **OpenAI**: If `"gpt"` in `model` name → uses `ChatOpenAI`
- **Ollama**: Otherwise → uses `ChatOllama` with `OLLAMA_BASE_URL`

Default: `http://localhost:11434` for local Ollama models (llama3.2, mistral, etc.)

### Tool Parameter Extraction

`Tool.format_description()` (lines 26-67) generates structured prompts with:
- Required vs. optional parameters marked
- Example values inferred from param names/types (line 71-102)
- Usage examples in JSON format

Use `Tool.get_required_parameters()` to validate args before execution.

## File Structure Reference

```
main.py                      # Entrypoint: async main(), signal handlers, startup validation
servers_config.json          # MCP server configs + allowedTools whitelist
prompts/prompts_config.yaml  # All LLM prompts with server-specific overrides
utils/
  ├── slackbot.py           # Core: Intent analysis → execution → refusal logic
  ├── elicitation.py        # Intent analysis LLM call + clarification handling
  ├── chatbot.py            # LLM client (OpenAI/Ollama)
  ├── server.py             # MCP client wrapper (stdio/HTTP)
  ├── tool.py               # Tool representation with access control
  ├── config.py             # Environment + JSON config loading
  └── prompt_manager.py     # YAML prompt loading + server customization
```

## Testing Guidelines

**Current state**: No test files exist. When adding tests:

1. Mock MCP servers with `Tool(name, description, schema, config, is_allowed=True)`
2. Test intent analysis with various query patterns (see `prompts_config.yaml` examples)
3. Test access control: ensure `is_allowed=False` tools never execute
4. Test both transport modes (stdio/HTTP) with connection failures

## Common Pitfalls

1. **DO NOT** make second LLM call for conversational queries - intent analysis already decided
2. **DO NOT** modify `system_intent_analysis` prompt without understanding the three outcomes
3. **DO NOT** forget to filter tools by `is_allowed` before presenting to LLM or executing
4. **DO NOT** assume all MCP servers return same tuple length - check `is_http` first

## Dependencies & Environment

- **Slack SDK**: `slack_bolt` (AsyncApp, socket mode for real-time events)
- **MCP SDK**: `mcp` v1.0+ (ClientSession, stdio/HTTP clients)
- **LangChain**: LLM abstraction layer (`langchain-openai`, `langchain-ollama`)
- **Python 3.8+**: Heavy use of async/await, type hints

Environment variables in `.env` (see `.env.example` or README.md for full list).
