import os
import asyncio
import warnings
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.tools.retriever import create_retriever_tool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from tools.search import get_vectorstore
from servers.mcp_client import load_all_mcp_tools
from utils import TimeRangeParser
from prompts.builder import PromptBuilder

# Suppress warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

# Initialize utilities
time_parser = TimeRangeParser(timezone="UTC")  # Adjust timezone as needed

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
    description="Search runbooks and infrastructure documentation. Use this to find troubleshooting guides, operational procedures, and best practices.",
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

print(f"Total: {len(mcp_tools)} MCP tools loaded\n")

# Combine all tools
all_tools = [retriever_tool] + mcp_tools

# Build dynamic system prompt
prompt_builder = PromptBuilder()
system_prompt_text = prompt_builder.build_infrastructure_prompt(all_tools)

# Optional: Save generated prompt for debugging
if os.environ.get("DEBUG_PROMPT"):
    with open("generated_prompt.txt", "w") as f:
        f.write(system_prompt_text)
    print("Generated prompt saved to generated_prompt.txt\n")

# Create proper LangChain agent with tool calling
# Use SystemMessage to avoid template variable conflicts
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=system_prompt_text),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, all_tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=all_tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10
)

# Store conversation history per thread
conversation_history = {}


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
        # Parse time range if mentioned
        start_time, end_time = time_parser.parse(message)
        if start_time and end_time:
            logger.info(f"Parsed time range: {start_time} to {end_time}")

        # Get or create conversation history for this thread
        if thread_ts not in conversation_history:
            conversation_history[thread_ts] = []
        
        # Execute query with conversation memory
        response = agent_executor.invoke({
            "input": message,
            "chat_history": conversation_history[thread_ts]
        })
        
        response_text = response["output"]
        
        # Update conversation history
        conversation_history[thread_ts].append(HumanMessage(content=message))
        conversation_history[thread_ts].append(AIMessage(content=response_text))
        
        # Keep history limited to last 20 messages (10 exchanges)
        if len(conversation_history[thread_ts]) > 20:
            conversation_history[thread_ts] = conversation_history[thread_ts][-20:]
        
        say(text=response_text, thread_ts=thread_ts)
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        say(text=f"Sorry, I encountered an error: {str(e)}\n\nContact @platform-oncall if this persists.", thread_ts=thread_ts)


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
