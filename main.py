import asyncio
import json
import logging
import os
from typing import Dict, List, Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

# Set up basic logging
logging.basicConfig(level=logging.INFO)

class Config:
    """Simple configuration class for the bot"""
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Get required environment variables
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Get optional environment variables with defaults
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "llama2")
    
    def load_servers(self) -> Dict:
        """Load server configuration from JSON file"""
        try:
            with open("servers_config.json", "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading servers config: {e}")
            return {"mcpServers": {}}

class Tool:
    """Simple tool class for handling MCP tools"""
    def __init__(self, name: str, description: str, input_schema: Dict):
        self.name = name
        self.description = description
        self.input_schema = input_schema
    
    def format_description(self) -> str:
        """Format tool description for the LLM"""
        args = []
        if "properties" in self.input_schema:
            for name, info in self.input_schema["properties"].items():
                arg = f"- {name}: {info.get('description', 'No description')}"
                if name in self.input_schema.get("required", []):
                    arg += " (required)"
                args.append(arg)
        
        return f"""
Tool: {self.name}
Description: {self.description}
Arguments:
{chr(10).join(args)}
"""

class Server:
    """Handles MCP server connections"""
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.session = None
        self._stack = None
    
    async def start(self) -> None:
        """Start the server"""
        try:
            # Get the command to run
            cmd = "npx" if self.config["command"] == "npx" else self.config["command"]
            
            # Set up server parameters
            params = StdioServerParameters(
                command=cmd,
                args=self.config["args"],
                env=self.config.get("env")
            )
            
            # Start the server using async context managers properly
            client = stdio_client(params)
            self._stack = client
            self._context = await client.__aenter__()
            read, write = self._context
            
            session = ClientSession(read, write)
            self.session = session
            await session.__aenter__()
            await self.session.initialize()
            
        except Exception as e:
            logging.error(f"Error starting server {self.name}: {e}")
            await self.cleanup()
            raise
    
    async def get_tools(self) -> List[Tool]:
        """Get available tools from the server"""
        if not self.session:
            logging.error(f"Server {self.name} not initialized")
            return []
        
        tools = []
        try:
            response = await self.session.list_tools()
            for item in response:
                if isinstance(item, tuple) and item[0] == "tools":
                    for tool in item[1]:
                        tools.append(Tool(tool.name, tool.description, tool.inputSchema))
        except Exception as e:
            logging.error(f"Error getting tools: {e}")
        
        return tools
    
    async def run_tool(self, name: str, args: Dict) -> Any:
        """Run a tool with basic retry logic"""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not started")
        
        # Try twice with a 1 second delay between attempts
        for attempt in range(2):
            try:
                return await self.session.call_tool(name, args)
            except Exception as e:
                if attempt == 0:  # Only retry once
                    logging.info(f"Retrying tool {name} after error: {e}")
                    await asyncio.sleep(1)
                else:
                    raise
    
    async def cleanup(self) -> None:
        """Clean up server resources"""
        try:
            if self.session:
                try:
                    await self.session.__aexit__(None, None, None)
                except Exception as e:
                    logging.error(f"Error closing session: {e}")
                self.session = None
                
            if self._stack:
                try:
                    await self._stack.__aexit__(None, None, None)
                except Exception as e:
                    logging.error(f"Error closing stdio client: {e}")
                self._stack = None
                self._context = None
                
        except Exception as e:
            logging.error(f"Error during server cleanup: {e}")

class ChatBot:
    """Simple LLM client for chat interactions"""
    def __init__(self, api_key: str, model: str, ollama_url: str):
        self.api_key = api_key
        self.model = model
        self.ollama_url = ollama_url
    
    async def get_response(self, messages: List[Dict[str, str]]) -> str:
        """Get a response from the LLM"""
        try:
            # Set up the right model
            if "gpt" in self.model.lower():
                llm = ChatOpenAI(
                    api_key=self.api_key,
                    model_name=self.model,
                    temperature=0.7
                )
            else:
                llm = ChatOllama(
                    model=self.model,
                    base_url=self.ollama_url,
                    temperature=0.7
                )
            
            # Convert messages to LangChain format
            chain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    chain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    chain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chain_messages.append(AIMessage(content=msg["content"]))
            
            # Get response
            response = await llm.ainvoke(chain_messages)
            if isinstance(response, (str, list, dict)):
                return str(response)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logging.error(f"Error getting LLM response: {e}")
            if "connection refused" in str(e).lower():
                return "Error: Could not connect to the AI model. Is it running?"
            return f"Sorry, there was an error: {str(e)}"

class SlackBot:
    """Main Slack bot class"""
    def __init__(self, bot_token: str, app_token: str, servers: List[Server], chat_bot: ChatBot):
        self.app = AsyncApp(token=bot_token)
        self.socket_handler = AsyncSocketModeHandler(self.app, app_token)
        self.client = AsyncWebClient(token=bot_token)
        self.servers = servers
        self.chat_bot = chat_bot
        self.tools = []
        self.conversations = {}
        self.bot_id = None

        # Set up message handlers
        self.app.event("app_mention")(self.handle_mention)
        self.app.message()(self.handle_message)
    
    async def start(self) -> None:
        """Start the bot"""
        print("\n🔄 Initializing bot and loading tools...")
        
        # Initialize servers and get tools
        for server in self.servers:
            try:
                await server.start()
                new_tools = await server.get_tools()
                self.tools.extend(new_tools)
                print(f"\n📦 Loaded {len(new_tools)} tools from server '{server.name}':")
                for tool in new_tools:
                    print(f"   • {tool.name}: {tool.description}")
            except Exception as e:
                logging.error(f"Server error: {e}")
        
        # Print total tools loaded
        print(f"\n✨ Total tools available: {len(self.tools)}")
        
        # Get bot ID
        try:
            auth = await self.client.auth_test()
            self.bot_id = auth["user_id"]
            print(f"🤖 Bot connected successfully with ID: {self.bot_id}")
        except Exception as e:
            logging.error(f"Auth error: {e}")
            raise  # Re-raise to prevent running with invalid auth
        
        # Monitor socket connection
        async def on_connect(client, event):
            logging.info("🟢 Bot connected to Slack")
            return None
        
        async def on_disconnect(client, event):
            logging.warning("🔴 Bot disconnected from Slack")
            return None
        
        async def on_error(client, event):
            logging.error(f"❌ Socket error: {event.get('error', 'Unknown error')}")
            return None
        
        # Register connection monitors
        self.app.event("connecting")(on_connect)
        self.app.event("disconnecting")(on_disconnect)
        self.app.error(on_error)
        
        # Start listening for messages with automatic reconnection
        await self.socket_handler.start_async()
    
    async def handle_mention(self, event, say):
        """Handle when someone mentions the bot"""
        await self.process_message(event, say)
    
    async def handle_message(self, message, say):
        """Handle direct messages"""
        if message.get("channel_type") == "im":
            await self.process_message(message, say)
    
    async def process_message(self, event, say):
        """Process a message and respond"""
        # Skip bot's own messages
        if event.get("user") == self.bot_id:
            return
            
        # Log only essential message info
        message_log = {
            "type": event.get("type"),
            "channel": event.get("channel"),
            "user": event.get("user"),
            "text": event.get("text"),
            "ts": event.get("ts")
        }
        print("\n📩 Message:", json.dumps(message_log, indent=2))
        
        channel = event["channel"]
        text = event.get("text", "").replace(f"<@{self.bot_id}>", "").strip()
        thread = event.get("thread_ts", event.get("ts"))
        
        try:
            # Set up or get conversation history
            if channel not in self.conversations:
                self.conversations[channel] = []
            
            # Create system message with tools info
            tools_info = "\n".join(tool.format_description() for tool in self.tools)
            system_msg = {
                "role": "system",
                "content": f"You are a helpful assistant with these tools:\n{tools_info}\n\n"
                          f"To use a tool, format like this:\n[TOOL] tool_name\n{{\"param\": \"value\"}}"
            }
            
            # Add user message to history
            self.conversations[channel].append({"role": "user", "content": text})
            
            # Get AI response
            messages = [system_msg] + self.conversations[channel][-5:]  # Last 5 messages
            response = await self.chat_bot.get_response(messages)
            
            # Handle tool usage if needed
            if "[TOOL]" in response:
                response = await self.handle_tool(response, channel)
            
            # Save response and send it
            self.conversations[channel].append({"role": "assistant", "content": response})
            
            # Log only the response text
            print("💬 Response:", response.replace('\n', ' ')[:100] + ('...' if len(response) > 100 else ''))
            
            await say(text=response, thread_ts=thread)
            
        except Exception as e:
            error_msg = f"Sorry, something went wrong: {str(e)}"
            logging.error(f"Error handling message: {e}")
            await say(text=error_msg, thread_ts=thread)
    
    async def handle_tool(self, response: str, channel: str) -> str:
        """Handle a tool call in the response"""
        try:
            # Get tool name and args
            tool_text = response.split("[TOOL]")[1].strip()
            name = tool_text.split("\n")[0].strip()
            args = json.loads(tool_text.split("\n")[1])
            
            # Find server with this tool
            for server in self.servers:
                if any(t.name == name for t in await server.get_tools()):
                    result = await server.run_tool(name, args)
                    
                    # Get AI interpretation of result
                    messages = [
                        {"role": "system", "content": "Explain this tool result clearly:"},
                        {"role": "user", "content": f"Tool {name} returned: {result}"}
                    ]
                    return await self.chat_bot.get_response(messages)
            
            return f"Sorry, couldn't find tool: {name}"
            
        except Exception as e:
            logging.error(f"Tool error: {e}")
            return f"Sorry, there was an error using the tool: {str(e)}"

async def shutdown(bot):
    """Gracefully shutdown the bot and cleanup resources"""
    print("\n🔄 Shutting down bot...")
    
    if not bot:
        return
    
    try:
        # First cleanup servers to ensure proper resource cleanup
        for server in bot.servers:
            print(f"🧹 Cleaning up server: {server.name}")
            try:
                await server.cleanup()
            except Exception as e:
                print(f"Warning: Error cleaning up server {server.name}: {e}")
        
        # Then close Slack connections
        if hasattr(bot, 'socket_handler') and bot.socket_handler:
            print("👋 Closing Slack connection...")
            try:
                await bot.socket_handler.client.close()  # Close WebSocket client first
            except Exception as e:
                print(f"Warning: Error closing WebSocket client: {e}")
                
            try:
                if hasattr(bot, 'client'):
                    await bot.client.close()  # Close HTTP client
            except Exception as e:
                print(f"Warning: Error closing HTTP client: {e}")
                
        print("✨ Shutdown complete!")
        
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")

async def main():
    """Main function to run the bot"""
    bot = None
    try:
        # Load config
        print("📚 Loading configuration...")
        config = Config()
        
        # Check required tokens
        if not config.slack_bot_token or not config.slack_app_token:
            print("❌ Error: Missing Slack tokens in .env file")
            return
        
        # Set up components
        print("🔧 Setting up components...")
        server_config = config.load_servers()
        servers = [Server(name, cfg) for name, cfg in server_config["mcpServers"].items()]

        if not config.openai_api_key:
            print("❌ Error: Missing OpenAI API key in .env file")
            return
            
        chat_bot = ChatBot(config.openai_api_key, config.model, config.ollama_url)
        
        # Create and start bot
        bot = SlackBot(config.slack_bot_token, config.slack_app_token, servers, chat_bot)
        
        print("🚀 Starting bot...")
        await bot.start()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Received shutdown signal (Ctrl+C)")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if bot:
            await shutdown(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This catches Ctrl+C during asyncio.run()
        pass