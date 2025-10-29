import json
import logging
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from utils.config import Config
from utils.server import Server
from utils.chatbot import ChatBot


@dataclass
class PendingRequest:
    tool_name: str
    question: str
    original_query: str


class SlackBot:
    def __init__(self, bot_token: str, app_token: str, servers: List[Server], chat_bot: ChatBot, config: Config):
        self.app = AsyncApp(token=bot_token)
        self.socket_handler = AsyncSocketModeHandler(self.app, app_token)
        self.client = AsyncWebClient(token=bot_token)
        self.servers = servers
        self.chat_bot = chat_bot
        self.config = config
        self.tools = []
        self.conversations = {}
        self.pending_requests = {}
        self.bot_id = None

        self.app.event("app_mention")(self.handle_mention)
        self.app.message()(self.handle_message)

    async def start(self) -> None:
        print("\n🔄 Initializing bot and loading tools...")
        
        connected_servers = 0
        for server in self.servers:
            try:
                await asyncio.wait_for(server.start(), timeout=10.0)
                if server.session:
                    connected_servers += 1
                    new_tools = await server.get_tools()
                    allowed_tools = [tool for tool in new_tools if tool.is_allowed]
                    self.tools.extend(allowed_tools)
                    
                    if allowed_tools:
                        print(f"\n📦 Loaded {len(allowed_tools)} tools from '{server.name}':")
                        for tool in allowed_tools:
                            print(f"   • {tool.name}")
            except asyncio.TimeoutError:
                print(f"\n⚠️  Timeout connecting to '{server.name}'")
            except Exception as e:
                print(f"\n⚠️  Could not connect to '{server.name}': {e}")
        
        if connected_servers == 0:
            print("\n⚠️  Warning: No MCP servers connected successfully!")
        else:
            print(f"\n✅ Connected to {connected_servers}/{len(self.servers)} server(s)")
        
        print(f"✨ Total tools available: {len(self.tools)}")
        
        try:
            auth = await self.client.auth_test()
            self.bot_id = auth["user_id"]
            print(f"🤖 Bot connected successfully with ID: {self.bot_id}")
        except Exception as e:
            logging.error(f"Auth error: {e}")
            raise
        
        await self.socket_handler.start_async()

    async def handle_mention(self, event, say):        
        await self.socket_handler.start_async()

    async def handle_mention(self, event, say):
        await self.process_message(event, say)

    async def handle_message(self, message, say):
        if message.get("channel_type") == "im":
            await self.process_message(message, say)

    async def process_message(self, event, say):
        if event.get("user") == self.bot_id:
            return
        
        channel = event["channel"]
        user = event.get("user")
        text = event.get("text", "").replace(f"<@{self.bot_id}>", "").strip()
        thread = event.get("thread_ts", event.get("ts"))
        conversation_key = f"{channel}:{user}"
        
        # Get channel name for better logging
        try:
            channel_info = await self.client.conversations_info(channel=channel)
            channel_name = channel_info.get("channel", {}).get("name", channel)
        except:
            # Fallback to channel ID if we can't get the name (e.g., DM)
            channel_name = "DM" if event.get("channel_type") == "im" else channel
        
        print(f"\n📩 Message from {user} in #{channel_name}: {text}")
        
        try:
            if conversation_key not in self.conversations:
                self.conversations[conversation_key] = []
            
            if channel in self.pending_requests:
                pending = self.pending_requests[channel]
                tool_name, args = await self._parse_clarification_response(text, pending.tool_name)
                
                if args:
                    result = await self.execute_tool(tool_name, args, channel)
                    self.conversations[conversation_key].append({"role": "user", "content": text})
                    self.conversations[conversation_key].append({"role": "assistant", "content": result})
                    await say(text=result, thread_ts=thread)
                    del self.pending_requests[channel]
                else:
                    await say(text="Could not parse that. Please try again or ask for help.", thread_ts=thread)
                    del self.pending_requests[channel]
                return
            
            tool_name, args, clarification = await self._analyze_intent(
                text, self.tools, self.conversations.get(conversation_key, [])
            )
            
            self.conversations[conversation_key].append({"role": "user", "content": text})
            
            if clarification:
                self.pending_requests[channel] = PendingRequest(tool_name or "", clarification, text)
                await say(text=clarification, thread_ts=thread)
                return
            
            if tool_name == "GREETING":
                response = self._generate_greeting()
                self.conversations[conversation_key].append({"role": "assistant", "content": response})
                await say(text=response, thread_ts=thread)
                return
            
            if tool_name and args is not None:
                result = await self.execute_tool(tool_name, args, channel)
                if not result or result.strip() == "":
                    result = "Tool executed successfully but returned no result."
                self.conversations[conversation_key].append({"role": "assistant", "content": result})
                await say(text=result, thread_ts=thread)
                return
            
            if text.lower() in ["help", "what can you do", "list tools"]:
                response = self._generate_greeting()
                self.conversations[conversation_key].append({"role": "assistant", "content": response})
                await say(text=response, thread_ts=thread)
                return
            
            response = f"I don't have access to that. I can help with: {', '.join(t.name for t in self.tools[:5])}"
            self.conversations[conversation_key].append({"role": "assistant", "content": response})
            await say(text=response, thread_ts=thread)
            
        except Exception as e:
            logging.error(f"Error processing message: {e}", exc_info=True)
            await say(text=f"Sorry, something went wrong: {str(e)}", thread_ts=thread)

    async def _analyze_intent(
        self, 
        user_query: str, 
        available_tools: List,
        conversation_history: List[Dict] = None
    ) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        if not available_tools:
            return None, None, None
        
        tools_info = "\n".join([
            f"- {tool.name}: {tool.description}\n  Parameters: {tool.get_parameter_info()}"
            for tool in available_tools
        ])
        
        system_prompt = f"""Analyze the user query and determine if they want to use a tool.

Available tools:
{tools_info}

Return a JSON response with:
- "tool_name": name of the tool to use, "GREETING" for greetings, or null if no tool matches
- "args": tool arguments as dict, or null if missing parameters
- "clarification": question to ask user if more info needed, or null if ready

Return valid JSON only, no other text."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User query: {user_query}"}
        ]
        
        response = await self.chat_bot.get_response(messages)
        
        try:
            # Extract JSON from response (LLM might add thinking tags or extra text)
            # Find the first { and last } to get the complete JSON object
            import re
            
            # Remove <think> tags if present
            cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
            
            # Find JSON object
            start = cleaned.find('{')
            if start == -1:
                logging.warning(f"No JSON object found in LLM response")
                return None, None, None
            
            # Find matching closing brace
            brace_count = 0
            end = start
            for i in range(start, len(cleaned)):
                if cleaned[i] == '{':
                    brace_count += 1
                elif cleaned[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if brace_count != 0:
                logging.warning(f"Unmatched braces in JSON")
                return None, None, None
            
            json_str = cleaned[start:end]
            data = json.loads(json_str)
            return data.get("tool_name"), data.get("args"), data.get("clarification")
            
        except Exception as e:
            logging.warning(f"Failed to parse LLM response: {e}")
            return None, None, None

    async def _parse_clarification_response(self, response: str, tool_name: str) -> Tuple[Optional[str], Optional[Dict]]:
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            return None, None
        
        system_prompt = f"""Extract parameters from the user's response for the tool '{tool_name}'.
        
Tool parameters: {tool.get_parameter_info()}

Return JSON with extracted parameters as dict, or empty dict if cannot parse."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": response}
        ]
        
        result = await self.chat_bot.get_response(messages)
        
        try:
            # Extract JSON from response (LLM might add thinking tags or extra text)
            import re
            
            # Remove <think> tags if present
            cleaned = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
            
            # Find JSON object
            start = cleaned.find('{')
            if start == -1:
                return None, None
            
            # Find matching closing brace
            brace_count = 0
            end = start
            for i in range(start, len(cleaned)):
                if cleaned[i] == '{':
                    brace_count += 1
                elif cleaned[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if brace_count != 0:
                return None, None
            
            json_str = cleaned[start:end]
            args = json.loads(json_str)
            return tool_name, args if args else None
            
        except:
            return None, None

    async def execute_tool(self, tool_name: str, args: Dict, channel: str) -> str:
        try:
            # Check if tool is allowed
            if not any(t.name == tool_name and t.is_allowed for t in self.tools):
                logging.warning(f"🚫 Blocked execution of disallowed tool: {tool_name}")
                return f"Tool '{tool_name}' is not available."
            
            logging.info(f"✅ Executing allowed tool: {tool_name} with args: {args}")
            
            for server in self.servers:
                server_tools = await server.get_tools()
                if any(t.name == tool_name and t.is_allowed for t in server_tools):
                    result = await server.run_tool(tool_name, args)
                    result_text = self._extract_text(result)
                    
                    if not result_text or result_text.strip() == "":
                        return "Tool executed but returned no data."
                    
                    system_prompt = f"Format this tool result as a helpful Slack message:\n\nResult: {result_text}"
                    messages = [{"role": "system", "content": system_prompt}]
                    
                    interpretation = await self.chat_bot.get_response(messages)
                    
                    if not interpretation or interpretation.strip() == "":
                        return result_text
                    
                    return interpretation
            
            return f"Tool '{tool_name}' not found."
        except Exception as e:
            logging.error(f"Tool execution error: {e}", exc_info=True)
            return f"Error executing tool: {str(e)}"

    def _extract_text(self, result) -> str:
        try:
            if hasattr(result, 'content') and isinstance(result.content, list):
                return '\n'.join(item.text for item in result.content if hasattr(item, 'text'))
            return str(result)
        except:
            return str(result)

    def _generate_greeting(self) -> str:
        if not self.tools:
            return "Hi! I'm ready to help, but no tools are available right now."
        
        # Group tools by server to show diverse capabilities
        tools_by_server = {}
        for tool in self.tools:
            # Extract server name from tool or use a generic key
            server_name = getattr(tool, 'server_name', 'default')
            if server_name not in tools_by_server:
                tools_by_server[server_name] = []
            tools_by_server[server_name].append(tool)
        
        # Select tools: try to get at least one from each server
        selected_tools = []
        max_per_server = max(1, 5 // len(tools_by_server)) if len(tools_by_server) > 0 else 5
        
        for server_tools in tools_by_server.values():
            selected_tools.extend(server_tools[:max_per_server])
            if len(selected_tools) >= 5:
                break
        
        # If still less than 5, fill up from remaining tools
        if len(selected_tools) < 5:
            for tool in self.tools:
                if tool not in selected_tools:
                    selected_tools.append(tool)
                    if len(selected_tools) >= 5:
                        break
        
        # Format tools with proper descriptions and server attribution
        tool_lines = []
        for t in selected_tools[:5]:
            # Get first line of description and truncate nicely
            desc = t.description.split('\n')[0].strip()
            if len(desc) > 100:
                desc = desc[:97] + "..."
            server_badge = f" *[{t.server_name}]*" if hasattr(t, 'server_name') and t.server_name else ""
            tool_lines.append(f"• `{t.name}`{server_badge}: {desc}")
        
        tool_list = "\n".join(tool_lines)
        
        # Add a summary line showing total capabilities
        total_tools = len(self.tools)
        servers_count = len(tools_by_server)
        summary = f"\n\n_({total_tools} tools available from {servers_count} server(s))_"
        
        return f"Hello! 👋 I can help with:\n\n{tool_list}{summary}"
