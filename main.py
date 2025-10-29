import os
import sys
import asyncio
import warnings

# Suppress MCP SDK cleanup warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*Attempted to exit cancel scope.*")

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

load_dotenv()

bot_token = os.environ.get("SLACK_BOT_TOKEN")
app_token = os.environ.get("SLACK_APP_TOKEN")
llm_model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

if not bot_token or not app_token:
    raise ValueError(
        "Missing required environment variables: SLACK_BOT_TOKEN and/or SLACK_APP_TOKEN"
    )

app = App(token=bot_token)

# Initialize the LLM based on configuration
if llm_model.startswith("gpt"):
    # Use OpenAI model
    llm = ChatOpenAI(model=llm_model, temperature=0)
else:
    # Use Ollama model
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = ChatOllama(
        model=llm_model,
        base_url=ollama_base_url,
        temperature=0
    )

vectorstore = get_vectorstore()
retriever_tool = create_retriever_tool(
    vectorstore.as_retriever(),
    name="search",
    description="Retrieve information about the company. You will call this tool when you need to answer a question that you do not know the answer to.",
)

# Load MCP tools from servers (handles unavailable servers gracefully)
print("\n=== Loading MCP Servers ===")

# Temporarily suppress stderr to hide async cleanup warnings
import sys
old_stderr = sys.stderr
sys.stderr = open(os.devnull, 'w')
try:
    mcp_tools = asyncio.run(load_all_mcp_tools())
finally:
    sys.stderr.close()
    sys.stderr = old_stderr

print("===========================\n")

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
def handle_hello(body, say):
    event = body["event"]
    message = event["text"]
    thread_ts = event.get("thread_ts", event["ts"])

    # Check if user is asking for help
    if "help" in message.lower():
        # List all available tools
        tool_list = []
        for tool in all_tools:
            tool_name = tool.name
            # Get first meaningful line of description
            lines = tool.description.strip().split('\n')
            tool_desc = lines[0].strip() if lines else "No description"
            # If first line is too short (like just a title), try to get more context
            if len(tool_desc) < 20 and len(lines) > 1:
                tool_desc = lines[1].strip()
            # Truncate if still too long
            if len(tool_desc) > 80:
                tool_desc = tool_desc[:77] + "..."
            tool_list.append(f"• *{tool_name}*: {tool_desc}")
        
        help_text = "Here are the tools available:\n" + "\n".join(tool_list)
        help_text += "\n\nFor more details, feel free to ask!"
        say(text=help_text, thread_ts=thread_ts)
        return

    # Add system prompt to the conversation
    response = agent.invoke({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    })
    text = response["messages"][-1].content

    say(text=text, thread_ts=thread_ts)

if __name__ == "__main__":
    try:
        handler = SocketModeHandler(app, app_token)
        handler.start()
    except (KeyboardInterrupt, RuntimeError):
        # Suppress cleanup errors from MCP SDK
        pass
