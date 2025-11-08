import os
import asyncio
import warnings
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langgraph.prebuilt import create_react_agent
from langchain.tools.retriever import create_retriever_tool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from tools.search import get_vectorstore
from tools.math import tools as math_tools
from servers.mcp_client import load_all_mcp_tools

# Suppress warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

# Determine environment and select appropriate tokens
environment = os.environ.get("ENVIRONMENT", "prod").lower()

if environment == "dev":
    bot_token = os.environ.get("SLACK_BOT_TOKEN_DEV")
    app_token = os.environ.get("SLACK_APP_TOKEN_DEV")
    print("🔧 Running in DEVELOPMENT mode")
else:
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    print("🚀 Running in PRODUCTION mode")

if not bot_token or not app_token:
    raise ValueError(
        f"Missing required environment variables for {environment.upper()} environment. "
        f"Need: SLACK_BOT_TOKEN{'_DEV' if environment == 'dev' else ''} and SLACK_APP_TOKEN{'_DEV' if environment == 'dev' else ''}"
    )

llm_model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

app = App(token=bot_token)

# Initialize the LLM based on configuration
if llm_model.startswith("gpt"):
    llm = ChatOpenAI(model=llm_model, temperature=0)
else:
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = ChatOllama(model=llm_model, base_url=ollama_base_url, temperature=0)

vectorstore = get_vectorstore()
retriever_tool = create_retriever_tool(
    vectorstore.as_retriever(),
    name="search",
    description="Retrieve information about the company. You will call this tool when you need to answer a question that you do not know the answer to.",
)

# Load MCP tools from servers (handles unavailable servers gracefully)
print("Loading MCP servers...")

# Suppress stderr during MCP loading to hide cleanup errors
import sys
from io import StringIO
old_stderr = sys.stderr
sys.stderr = StringIO()

try:
    mcp_tools = asyncio.run(load_all_mcp_tools())
finally:
    sys.stderr = old_stderr

print(f"Loaded {len(mcp_tools)} MCP tools")


# Combine all tools
all_tools = [retriever_tool] + math_tools + mcp_tools

# System prompt to guide tool usage
system_prompt = """You are a helpful assistant with access to these tools:

1. **search** - Search company information, FAQs, policies, office hours, etc.
2. **add_numbers**, **subtract_numbers**, **multiply_numbers** - Perform basic math
3. **MCP tools** - Get cryptocurrency prices, monitoring data, etc.

IMPORTANT: Always use the appropriate tool when available. For example:
- Company questions → use "search" tool
- Math problems → use math tools  
- Crypto prices → use MCP tools
- Office hours, policies, company info → use "search" tool

If the user asks something completely unrelated (like weather, sports, general knowledge), politely say you can only help with the topics covered by your tools.

Always try to use a tool first before saying you can't help."""

agent = create_react_agent(llm, tools=all_tools)


@app.event("message")
def handle_message_events(body, logger):
    """Handle general message events."""
    logger.info(body)


@app.event("app_mention")
def handle_app_mention(body, say, logger):
    """Handle app mention events."""
    event = body["event"]
    message = event["text"]
    thread_ts = event.get("thread_ts", event["ts"])

    try:
        # Check if user is asking for help
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in ["help", "list tools", "what can you do"]):
            help_text = "*Available Tools:*\n\n"
            for tool in all_tools:
                help_text += f"• `{tool.name}` - {tool.description.split('.')[0]}\n"
            help_text += "\n_Mention me with your question to use these tools_"
            say(text=help_text, thread_ts=thread_ts)
            return

        # Add system prompt to the conversation
        response = agent.invoke({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        })
        
        response_text = response["messages"][-1].content
        say(text=response_text, thread_ts=thread_ts)
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        say(text="I encountered an error processing your request. Please try again.", thread_ts=thread_ts)


if __name__ == "__main__":
    try:
        handler = SocketModeHandler(app, app_token)
        print(f"Bot is running in {environment.upper()} mode...")
        handler.start()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        # Suppress cleanup errors from MCP SDK
        pass
