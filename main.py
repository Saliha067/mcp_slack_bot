import os
import sys
import asyncio
import warnings
import time

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
from formatters.response_formatter import SlackResponseFormatter
from guardrails.input_guardrails import GuardrailChain

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

# Initialize guardrails
guardrail_chain = GuardrailChain()


@app.event("message")
def handle_message_events(body, logger):
    """Handle general message events."""
    logger.info(body)


@app.event("app_mention")
def handle_hello(body, say, logger):
    event = body["event"]
    message = event["text"]
    user_id = event["user"]
    thread_ts = event.get("thread_ts", event["ts"])

    try:
        # Run guardrails check
        guardrail_result = guardrail_chain.check_all(
            message=message,
            user_id=user_id,
            timestamp=time.time()
        )
        
        if not guardrail_result.passed:
            # Guardrail failed - send error message
            error_response = SlackResponseFormatter.format_error_message(
                guardrail_result.reason,
                context=f"Severity: {guardrail_result.severity}"
            )
            say(**error_response, thread_ts=thread_ts)
            logger.warning(f"Guardrail blocked message from {user_id}: {guardrail_result.reason}")
            return
        
        # Check if user is asking for help or list of tools
        message_lower = message.lower()
        help_keywords = ["help", "list of tools", "available tools", "what can you do", "show tools", "list tools"]
        if any(keyword in message_lower for keyword in help_keywords):
            # Use formatter for help message
            formatted_help = SlackResponseFormatter.format_help_message(all_tools)
            say(**formatted_help, thread_ts=thread_ts)
            return

        # Add system prompt to the conversation
        response = agent.invoke({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        })
        response_text = response["messages"][-1].content
        
        # Extract tools used from the agent response
        tools_used = []
        for msg in response["messages"]:
            # Check for tool calls in additional_kwargs (OpenAI format)
            if hasattr(msg, "additional_kwargs") and "tool_calls" in msg.additional_kwargs:
                for tool_call in msg.additional_kwargs["tool_calls"]:
                    tool_name = tool_call.get("function", {}).get("name")
                    if tool_name and tool_name not in tools_used:
                        tools_used.append(tool_name)
            # Check for tool_calls attribute directly (LangGraph format)
            elif hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name")
                    if tool_name and tool_name not in tools_used:
                        tools_used.append(tool_name)
        
        # Log tools used for debugging
        if tools_used:
            logger.info(f"Tools used in this response: {', '.join(tools_used)}")
        else:
            logger.info("No tools were used in this response")
        
        # Format response based on complexity
        if SlackResponseFormatter.should_use_blocks(response_text):
            formatted_response = SlackResponseFormatter.format_agent_response(
                response_text,
                tools_used=tools_used if tools_used else None
            )
            say(**formatted_response, thread_ts=thread_ts)
        else:
            # Simple text response - add tool info if tools were used
            if tools_used:
                formatted_response = SlackResponseFormatter.format_agent_response(
                    response_text,
                    tools_used=tools_used,
                    include_metadata=True
                )
                say(**formatted_response, thread_ts=thread_ts)
            else:
                say(text=response_text, thread_ts=thread_ts)
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        error_response = SlackResponseFormatter.format_error_message(
            "I encountered an error processing your request. Please try again.",
            context=f"Error type: {type(e).__name__}"
        )
        say(**error_response, thread_ts=thread_ts)

if __name__ == "__main__":
    try:
        handler = SocketModeHandler(app, app_token)
        handler.start()
    except (KeyboardInterrupt, RuntimeError):
        # Suppress cleanup errors from MCP SDK
        pass
