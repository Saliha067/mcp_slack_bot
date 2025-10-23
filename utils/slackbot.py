"""SlackBot class for handling Slack interactions and orchestrating MCP tool usage."""
import asyncio
import json
import logging
import re
from typing import List, Dict

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from utils.config import Config
from utils.server import Server
from utils.chatbot import ChatBot
from utils.prompt_manager import PromptManager
from utils.elicitation import ElicitationHandler


class SlackBot:
    """Main Slack bot class"""
    def __init__(self, bot_token: str, app_token: str, servers: List[Server], chat_bot: ChatBot, config: Config):
        self.app = AsyncApp(token=bot_token)
        self.socket_handler = AsyncSocketModeHandler(self.app, app_token)
        self.client = AsyncWebClient(token=bot_token)
        self.servers = servers
        self.chat_bot = chat_bot
        self.config = config
        self.prompt_manager = PromptManager()
        self.elicitation_handler = ElicitationHandler(chat_bot, self.prompt_manager)  # Pass prompt_manager
        self.tools = []  # Allowed tools only
        self.all_tools = []  # All tools including disallowed ones
        self.conversations = {}
        self.bot_id = None

        # Set up message handlers
        self.app.event("app_mention")(self.handle_mention)
        self.app.message()(self.handle_message)
    
    def _generate_tool_capabilities_description(self) -> str:
        """Generate a dynamic description of tool capabilities for refusal messages (only allowed tools)"""
        allowed_tools = [tool for tool in self.tools if tool.is_allowed]
        
        if not allowed_tools:
            return "specific tasks"
        
        # Extract capabilities from tool descriptions
        capabilities = []
        
        for tool in allowed_tools[:5]:  # Limit to first 5 tools for brevity
            # Get first sentence or first 50 chars of description
            desc = tool.description.split('.')[0].split('\n')[0].strip()
            if len(desc) > 60:
                desc = desc[:57] + "..."
            if desc:  # Only add non-empty descriptions
                capabilities.append(desc.lower())
        
        # Format the list
        if not capabilities:
            # Fallback to tool names if descriptions are empty
            tool_names = [tool.name.replace('_', ' ') for tool in allowed_tools[:5]]
            if len(tool_names) == 1:
                return tool_names[0]
            elif len(tool_names) == 2:
                result = f"{tool_names[0]} and {tool_names[1]}"
            else:
                result = ", ".join(tool_names[:-1]) + f", and {tool_names[-1]}"
        elif len(capabilities) == 1:
            result = capabilities[0]
        elif len(capabilities) == 2:
            result = f"{capabilities[0]} and {capabilities[1]}"
        else:
            result = ", ".join(capabilities[:-1]) + f", and {capabilities[-1]}"
        
        # If we have more tools, add a note
        if len(allowed_tools) > 5:
            result += f" (and {len(allowed_tools) - 5} more)"
        
        return result
    
    async def start(self) -> None:
        """Start the bot"""
        print("\n🔄 Initializing bot and loading tools...")
        
        # Initialize servers and get tools
        for server in self.servers:
            try:
                await server.start()
                new_tools = await server.get_tools()
                
                # Store all tools for reference
                self.all_tools.extend(new_tools)
                
                # Filter to only allowed tools for execution
                allowed_tools = [tool for tool in new_tools if tool.is_allowed]
                self.tools.extend(allowed_tools)
                
                if allowed_tools:
                    print(f"\n📦 Loaded {len(allowed_tools)} tools from server '{server.name}':")
                    for tool in allowed_tools:
                        print(f"   • {tool.name}")
                        # Debug: log tool description
                        if tool.description:
                            desc_preview = tool.description[:80] + "..." if len(tool.description) > 80 else tool.description
                            logging.debug(f"     Description: {desc_preview}")
                        else:
                            logging.warning(f"     ⚠️  No description for tool: {tool.name}")
            except Exception as e:
                if server.is_http:
                    print(f"\n⚠️  Warning: Could not connect to HTTP server '{server.name}' at {server.config.get('url')}")
                    print(f"   Make sure the server is running. Skipping this server.")
                else:
                    print(f"\n⚠️  Warning: Failed to start server '{server.name}': {e}")
                logging.debug(f"Server error details: {e}")
        
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
        
        async def on_disconnect(client, event):
            logging.warning("🔴 Bot disconnected from Slack")
        
        async def on_error(error):
            """Handle Slack app errors"""
            error_msg = str(error) if error else "Unknown error"
            logging.error(f"❌ Slack error: {error_msg}")
        
        # Register connection monitors (these might not work with socket mode)
        try:
            self.app.event("connecting")(on_connect)
            self.app.event("disconnecting")(on_disconnect)
        except Exception as e:
            logging.debug(f"Could not register connection events: {e}")
        
        # Register error handler
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
        """Process a message and respond using intelligent elicitation"""
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
        user = event.get("user")
        text = event.get("text", "").replace(f"<@{self.bot_id}>", "").strip()
        thread = event.get("thread_ts", event.get("ts"))
        
        # Create a unique conversation key per user in channel
        # This ensures each user maintains their own conversation context
        conversation_key = f"{channel}:{user}"
        
        try:
            # Set up or get conversation history
            if conversation_key not in self.conversations:
                self.conversations[conversation_key] = []
            
            # Check if this is a response to a pending elicitation request
            if self.elicitation_handler.has_pending_request(channel):
                print("🔄 Processing clarification response...")
                pending = self.elicitation_handler.get_pending_request(channel)
                
                try:
                    # Handle the clarification response
                    tool_name, args, further_clarification = await self.elicitation_handler.handle_clarification_response(
                        channel, text, pending.tool_name, self.tools, pending
                    )
                    
                    if further_clarification:
                        # Still need more info
                        print(f"❓ Still need clarification: {further_clarification}")
                        await say(text=further_clarification, thread_ts=thread)
                        return
                    elif tool_name and args is not None:
                        # Ready to execute
                        print(f"✅ Ready to execute {tool_name} with args: {args}")
                        self.elicitation_handler.clear_pending_request(channel)
                        
                        # Execute the tool
                        result = await self.execute_tool(tool_name, args, channel, text)
                        
                        # Save to conversation history
                        self.conversations[conversation_key].append({"role": "user", "content": text})
                        self.conversations[conversation_key].append({"role": "assistant", "content": result})
                        
                        print("💬 Response:", result.replace('\n', ' ')[:100] + ('...' if len(result) > 100 else ''))
                        await say(text=result, thread_ts=thread)
                        return
                    elif tool_name is None and args is None and further_clarification is None:
                        # User asked something conversational/unrelated during clarification
                        # Clear pending and refuse (following architecture: no tool match → refuse)
                        print("⚠️  User asked unrelated question during clarification, refusing")
                        self.elicitation_handler.clear_pending_request(channel)
                        
                        refusal = self._generate_tool_capabilities_description()
                        await say(text=refusal, thread_ts=thread)
                        return
                    else:
                        # Couldn't parse the clarification response
                        # Clear pending and treat as new query
                        print("⚠️  Couldn't parse clarification response, treating as new query")
                        self.elicitation_handler.clear_pending_request(channel)
                        
                except Exception as e:
                    logging.error(f"Error handling clarification: {e}", exc_info=True)
                    self.elicitation_handler.clear_pending_request(channel)
                    await say(
                        text="Sorry, I had trouble understanding your response. Let's start over - what would you like me to help you with?",
                        thread_ts=thread
                    )
                    return
            
            # ═══════════════════════════════════════════════════════════════════════════
            # ARCHITECTURE DECISION POINT: Intent Analysis
            # ═══════════════════════════════════════════════════════════════════════════
            # This is the ONLY LLM call that decides what action to take.
            # Three possible outcomes:
            #   1. (tool_name, args, None) → Execute the tool immediately
            #   2. (tool_name, None, clarification) → Ask user for more info
            #   3. (None, None, None) → CONVERSATIONAL (no matching tool) → Refuse
            # 
            # This is the SINGLE source of truth. We trust the intent analysis LLM
            # and do NOT make any additional LLM calls or apply pattern matching.
            # ═══════════════════════════════════════════════════════════════════════════
            print("🔍 Analyzing user intent...")
            tool_name, args, clarification = await self.elicitation_handler.analyze_user_intent(
                text, self.tools, self.conversations.get(conversation_key, [])
            )
            
            # Add user message to history
            self.conversations[conversation_key].append({"role": "user", "content": text})
            
            # ═══════════════════════════════════════════════════════════════════════════
            # OUTCOME 1: Need Clarification
            # ═══════════════════════════════════════════════════════════════════════════
            # Intent analysis determined we need more information from the user.
            # Tool was identified but parameters are missing or ambiguous.
            # ═══════════════════════════════════════════════════════════════════════════
            if clarification:
                # Need clarification from user
                print(f"❓ Requesting clarification: {clarification}")
                self.elicitation_handler.create_elicitation_request(
                    channel, tool_name or "unknown", clarification, original_query=text
                )
                await say(text=clarification, thread_ts=thread)
                return
            
            # ═══════════════════════════════════════════════════════════════════════════
            # OUTCOME 2: Execute Tool or Handle Greeting
            # ═══════════════════════════════════════════════════════════════════════════
            # Intent analysis identified a matching tool with all required parameters,
            # or detected a greeting.
            # ═══════════════════════════════════════════════════════════════════════════
            if tool_name == "GREETING":
                # LLM detected a greeting - respond with friendly message + tool list
                print("👋 Greeting detected")
                allowed_tools = [tool for tool in self.tools if tool.is_allowed]
                
                if allowed_tools:
                    def get_brief_desc(desc):
                        lines = [line.strip() for line in desc.split('\n') if line.strip()]
                        if not lines:
                            return "No description"
                        return lines[0][:80] + "..." if len(lines[0]) > 80 else lines[0]
                    
                    tool_list = "\n".join([f"• `{tool.name}`: {get_brief_desc(tool.description)}" 
                                          for tool in allowed_tools])
                    
                    response = f"Hello! 👋 I'm here to assist you with various tasks.\n\n**Available tools:**\n{tool_list}"
                else:
                    response = "Hi there! 👋 I'm here to help, but I don't have any tools available at the moment."
                
                self.conversations[conversation_key].append({"role": "assistant", "content": response})
                await say(text=response, thread_ts=thread)
                return
            
            if tool_name and args is not None:
                # Ready to execute tool
                print(f"🔧 Executing tool: {tool_name} with args: {args}")
                
                # Validate tool call
                tool = next((t for t in self.tools if t.name == tool_name), None)
                if tool:
                    validation_error = await self.elicitation_handler.validate_tool_call(
                        tool_name, args, tool
                    )
                    
                    if validation_error:
                        # Missing required params
                        print(f"⚠️ Validation failed: {validation_error}")
                        self.elicitation_handler.create_elicitation_request(
                            channel, tool_name, validation_error, original_query=text
                        )
                        await say(text=validation_error, thread_ts=thread)
                        return
                
                # Execute the tool
                result = await self.execute_tool(tool_name, args, channel, text)
                
                # Save response and send it
                self.conversations[conversation_key].append({"role": "assistant", "content": result})
                print("💬 Response:", result.replace('\n', ' ')[:100] + ('...' if len(result) > 100 else ''))
                await say(text=result, thread_ts=thread)
                return
            
            # ═══════════════════════════════════════════════════════════════════════════
            # OUTCOME 3: CONVERSATIONAL (Refuse or Answer Meta-Query)
            # ═══════════════════════════════════════════════════════════════════════════
            # Intent analysis returned (None, None, None) meaning:
            # - No tool matches the query's purpose
            # - Query might be general knowledge, joke, math, web search, etc.
            # - OR user is asking about bot capabilities/tools (meta-query)
            #
            # Check if this is a meta-query about tools before refusing
            # ═══════════════════════════════════════════════════════════════════════════
            print("🚫 Query marked as CONVERSATIONAL (no matching tools)")
            
            # Check if user is asking about tools/capabilities (meta-query)
            text_lower = text.lower()
            is_help_query = "help" in text_lower and len(text_lower.split()) <= 3  # Simple "help" or "help me"
            is_list_query = any(keyword in text_lower for keyword in [
                "what tools", "list tools", "what can you", "what do you", "your capabilities",
                "available", "show me what", "not allowed", "restricted"
            ])
            
            if is_help_query:
                # User asking for help - show standard help message with tool list
                allowed_tools = [tool for tool in self.tools if tool.is_allowed]
                
                if allowed_tools:
                    def get_brief_desc(desc):
                        lines = [line.strip() for line in desc.split('\n') if line.strip()]
                        if not lines:
                            return "No description"
                        return lines[0][:80] + "..." if len(lines[0]) > 80 else lines[0]
                    
                    tool_list = "\n".join([f"• `{tool.name}`: {get_brief_desc(tool.description)}" 
                                          for tool in allowed_tools])
                    
                    response = f"Hello! I'm here to assist you with various tasks.\n\n**Available tools:**\n{tool_list}"
                else:
                    response = "I'm here to help! However, I don't have any tools available at the moment."
                    
            elif is_list_query:
                # User wants to see tool list - provide detailed list
                allowed_tools = [tool for tool in self.tools if tool.is_allowed]
                
                def get_brief_desc(desc):
                    lines = [line.strip() for line in desc.split('\n') if line.strip()]
                    if not lines:
                        return "No description"
                    return lines[0][:80] + "..." if len(lines[0]) > 80 else lines[0]
                
                if allowed_tools:
                    tool_list = "\n".join([f"• `{tool.name}`: {get_brief_desc(tool.description)}" 
                                          for tool in allowed_tools])
                    response = f"I can help with {len(allowed_tools)} tool{'s' if len(allowed_tools) > 1 else ''}:\n\n{tool_list}"
                else:
                    response = "I don't have any tools available at the moment."
            else:
                # Generate dynamic tool capabilities description for refusal message
                tool_capabilities_brief = self._generate_tool_capabilities_description()
                response = f"I don't have access to that information. I can only help with {tool_capabilities_brief}."
            
            # Save response and send it
            self.conversations[conversation_key].append({"role": "assistant", "content": response})
            print(f"💬 Response: {response[:100]}{'...' if len(response) > 100 else ''}")
            await say(text=response, thread_ts=thread)
            
        except Exception as e:
            error_msg = f"Sorry, something went wrong: {str(e)}"
            logging.error(f"Error handling message: {e}", exc_info=True)
            await say(text=error_msg, thread_ts=thread)
    
    async def execute_tool(self, tool_name: str, args: Dict, channel: str, original_query: str) -> str:
        """
        Execute a tool and return a natural language response.
        
        Args:
            tool_name: Name of the tool to execute
            args: Arguments for the tool
            channel: Slack channel ID
            original_query: Original user query for context
            
        Returns:
            Natural language response based on tool result
        """
        try:
            print(f"🔧 Executing Tool: {tool_name} with args {args}")
            
            # Check if tool is allowed
            if not any(t.name == tool_name and t.is_allowed for t in self.tools):
                return f"Sorry, the tool '{tool_name}' is not available or not allowed."
            
            # Find server with this tool
            for server in self.servers:
                server_tools = await server.get_tools()
                matching_tool = next((t for t in server_tools if t.name == tool_name and t.is_allowed), None)
                if matching_tool:
                    # Execute the tool
                    result = await server.run_tool(tool_name, args)
                    print(f"✅ Tool Result: {str(result)[:200]}")
                    
                    # Extract text content from result
                    result_text = self._extract_tool_result(result)
                    
                    print(f"📝 Sending result to LLM for interpretation...")
                    
                    # Check if result is large
                    is_large = self.prompt_manager.is_large_result(result_text)
                    
                    if is_large:
                        print(f"⚠️  Large response ({len(result_text)} chars), asking LLM to extract relevant info...")
                    
                    # Get prompts from PromptManager (with server-specific customization)
                    system_prompt = self.prompt_manager.get_system_interpret_prompt(
                        server_name=server.name,
                        is_large=is_large
                    )
                    
                    user_prompt = self.prompt_manager.get_user_interpret_prompt(
                        user_query=original_query,
                        tool_name=tool_name,
                        result=result_text,
                        server_name=server.name,
                        is_large=is_large
                    )
                    
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                    
                    interpretation = await self.chat_bot.get_response(messages)
                    print(f"💡 LLM Interpretation: {interpretation[:100]}")
                    return interpretation
            
            return f"Sorry, couldn't find tool: {tool_name}"
            
        except Exception as e:
            logging.error(f"Tool execution error: {e}", exc_info=True)
            return f"Sorry, there was an error executing the tool: {str(e)}"
    
    def _extract_tool_result(self, result) -> str:
        """Extract text content from tool result"""
        try:
            # Handle different result formats
            if hasattr(result, 'content'):
                # MCP result with content array
                if isinstance(result.content, list):
                    texts = []
                    for item in result.content:
                        if hasattr(item, 'text'):
                            texts.append(item.text)
                    return '\n'.join(texts)
            
            # Just convert to string if unknown format
            return str(result)
        except Exception as e:
            logging.error(f"Error extracting result: {e}")
            return str(result)
