# MCP Slack Bot Setup Guide

A Slack bot that integrates with MCP (Model Context Protocol) servers to provide intelligent query responses.


## Features

![demo](/attachments/output.gif)

## Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Slack workspace with admin access
- Ollama (for local LLM) or OpenAI API key

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Saliha067/mcp_slack_bot.git
cd mcp_slack_bot
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name your app and select workspace
4. Go to **OAuth & Permissions**:
   - Add Bot Token Scopes:
     - `app_mentions:read`
     - `chat:write`
     - `im:history`
     - `im:read`
     - `channels:history`
   - Install app to workspace
   - Copy **Bot User OAuth Token** (starts with `xoxb-`)
5. Go to **Socket Mode**:
   - Enable Socket Mode
   - Generate **App-Level Token** with `connections:write` scope
   - Copy token (starts with `xapp-`)
6. Go to **Event Subscriptions**:
   - Enable Events
   - Subscribe to: `app_mention`, `message.im`

### 4. Configure Environment

Create `.env` file:
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
OPENAI_API_KEY=sk-your-openai-key
LLM_MODEL=qwen2.5:7b
ENVIRONMENT=prod
```

**Environment Options:**
- `ENVIRONMENT=prod` - Only HTTP/Streamable MCP servers
- `ENVIRONMENT=dev` - All MCP server types (HTTP + stdio)

### 5. Configure MCP Servers

Edit `servers_config.json`:
```json
{
  "servers": [
    {
      "name": "VictoriaMetrics",
      "type": "http",
      "url": "http://localhost:3000/mcp",
      "allowedTools": ["query", "metrics", "labels"]
    }
  ]
}
```

### 6. Start Docker Services

```bash
docker-compose up -d
```

This starts:
- VictoriaMetrics (metrics database) on port 8428
- MCP-VictoriaMetrics (MCP server) on port 3000

### 7. Load Test Data (Optional)

```bash
chmod +x scripts/load_test_data.sh
./scripts/load_test_data.sh
```

### 8. Start Bot

```bash
python main.py
```

## Usage

### In Slack

**Mention the bot:**
```
@your-bot What's the CPU usage on server1?
```

**Direct message:**
```
List all available metrics
```

**Multi-server query:**
```
What's the Bitcoin price and show me CPU metrics?
```

### Generate Sample Questions

```bash
python scripts/generate_sample_questions.py
```

## Configuration

### Server Types

**HTTP/Streamable (Production):**
```json
{
  "name": "VictoriaMetrics",
  "type": "http",
  "url": "http://localhost:3000/mcp",
  "allowedTools": ["query", "metrics"]
}
```

**Stdio (Development only):**
```json
{
  "name": "LocalFilesystem",
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
  "allowedTools": []
}
```

### Tool Filtering

**Allow specific tools:**
```json
"allowedTools": ["query", "metrics", "labels"]
```

**Allow all tools:**
```json
"allowedTools": []
```

## Monitoring

**Check logs:**
```bash
# Look for tool filtering
grep "Loaded.*tools" 
grep "Blocked execution"
grep "Executing allowed tool"
```

**Expected output:**
```
✅ Loaded VictoriaMetrics (http) server
📦 Loaded 7 tools from 'VictoriaMetrics'
✅ Executing allowed tool: query with args: {...}
🚫 Blocked execution of disallowed tool: active_queries
```

## Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

## Troubleshooting

**Bot not responding:**
- Check Slack tokens in `.env`
- Verify bot is mentioned or in DM
- Check bot is invited to channel

**MCP server connection failed:**
- Verify Docker containers running: `docker-compose ps`
- Check MCP server URL in `servers_config.json`
- Test endpoint: `curl http://localhost:3000/mcp`

**Tool execution blocked:**
- Check `allowedTools` in `servers_config.json`
- Review logs for filtering messages
- Verify tool name matches exactly

## Project Structure

```
mcp_slackbot/
├── main.py                  # Bot entry point
├── .env                     # Environment variables
├── servers_config.json      # MCP server configuration
├── docker-compose.yml       # Docker services
├── requirements.txt         # Python dependencies
├── utils/
│   ├── slack_bot.py        # Slack integration
│   ├── server.py           # MCP server client
│   ├── chatbot.py          # LLM integration
│   ├── config.py           # Configuration loader
│   ├── tool.py             # Tool definitions
│   └── prompt_manager.py   # Prompt management
├── scripts/
│   ├── load_test_data.sh              # Load sample metrics
│   └── generate_sample_questions.py   # Generate test queries
└── prompts/
    └── prompts_config.yaml  # LLM prompts

```

## Adding New MCP Servers

1. Add to `servers_config.json`:
```json
{
  "name": "MyServer",
  "type": "http",
  "url": "http://localhost:8000/mcp",
  "allowedTools": ["tool1", "tool2"]
}
```

2. Restart bot:
```bash
python main.py
```

3. Generate questions:
```bash
python scripts/generate_sample_questions.py
```

## Security Notes

- Use `ENVIRONMENT=prod` in production (HTTP only)
- Configure `allowedTools` to limit tool access
- Never commit `.env` file
- Use secrets management for production
- Review tool execution logs regularly

## Support

- Issues: https://github.com/Saliha067/mcp_slack_bot/issues
- MCP Docs: https://modelcontextprotocol.io/
- Slack API: https://api.slack.com/

## Credits

[MCP Simple Chatbot example](https://github.com/modelcontextprotocol/python-sdk/tree/main/examples/clients/simple-chatbot).
