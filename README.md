# MCP Simple Slackbot

Call MCP server from Slack bot using LLMs to respond to messages and execute tools.

## Features

![demo](/attachments/output.gif)

- **AI-Powered Assistant**: Responds to messages in channels and DMs using LLM capabilities
- **MCP Integration**: Full access to MCP tools like SQLite database and web fetching
- **Multi-LLM Support**: Works with OpenAI, Groq, and Anthropic models
- **App Home Tab**: Shows available tools and usage information

## Setup

Install Dependencies
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate  

# Install project dependencies
pip install -r requirements.txt

3. Configure Environment Variables

create a .env file in the project root with your Slack and LLM API credentials

SLACK_BOT_TOKEN=xoxb-
SLACK_APP_TOKEN=xapp-
OPENAI_API_KEY=<<your-openai-key>>
# if LLM_MODEL is not gpt or gpt-xxxxx then it will use local ollama model
LLM_MODEL=llama3.2

# Run the bot directly
python main.py


The bot will Connect to all configured MCP servers in servers_config.json , Discover available tools , Start the Slack app in Socket Mode and Listen for mentions and direct messages

## Credits

[MCP Simple Chatbot example](https://github.com/modelcontextprotocol/python-sdk/tree/main/examples/clients/simple-chatbot).
