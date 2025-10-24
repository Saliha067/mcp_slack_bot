import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from .tool import Tool


class Server:
    def __init__(self, name: str, config: Dict, app_config):
        self.name = name
        self.config = config
        self.app_config = app_config
        self.session = None
        self.tools_cache = []
        self.is_http = "url" in config
        self._http_context = None
        self._session_context = None
        self._stdio_context = None
    
    async def start(self) -> None:
        if self.is_http:
            await self._start_http()
        else:
            await self._start_stdio()
    
    async def _start_http(self) -> None:
        url = self.config.get("url")
        if not url:
            raise ValueError(f"Server {self.name} missing 'url'")
        
        try:
            logging.info(f"Connecting to {self.name} at {url}")
            
            # Enter the streamablehttp_client context
            self._http_context = streamablehttp_client(url)
            read_stream, write_stream, get_session_id = await self._http_context.__aenter__()
            
            logging.info(f"Established HTTP connection to {self.name}")
            
            # Enter the ClientSession context
            self._session_context = ClientSession(read_stream, write_stream)
            self.session = await self._session_context.__aenter__()
            
            # Initialize the session
            logging.info(f"Initializing {self.name}...")
            await self.session.initialize()
            logging.info(f"✓ Initialized {self.name}")
            
        except Exception as e:
            logging.error(f"Failed to connect to {self.name}: {e}", exc_info=True)
            raise
    
    async def _start_stdio(self) -> None:
        command = self.config.get("command")
        args = self.config.get("args", [])
        
        if not command:
            raise ValueError(f"Server {self.name} missing 'command'")
        
        try:
            logging.info(f"Starting {self.name}")
            self._stdio_context = stdio_client(command, args)
            self.session = await self._stdio_context.__aenter__()
            
            logging.info(f"Initializing {self.name}...")
            await self.session.initialize()
            logging.info(f"✓ Initialized {self.name}")
        except Exception as e:
            logging.error(f"Failed to start {self.name}: {e}", exc_info=True)
            raise
    
    async def get_tools(self) -> List[Tool]:
        if not self.session:
            return []
        
        try:
            response = await self.session.list_tools()
            tools = []
            
            allowed_tools_list = getattr(self, 'allowed_tools', [])
            
            logging.info(f"Server {self.name} returned {len(response.tools)} total tools")
            if allowed_tools_list:
                logging.info(f"Filtering to allowed tools: {allowed_tools_list}")
            
            for tool_def in response.tools:
                allowed = not allowed_tools_list or tool_def.name in allowed_tools_list
                
                if not allowed:
                    logging.debug(f"Tool '{tool_def.name}' blocked - not in allowed list")
                
                tool = Tool(
                    name=tool_def.name,
                    description=tool_def.description or "",
                    input_schema=tool_def.inputSchema or {},
                    config=self.app_config,
                    is_allowed=allowed
                )
                tools.append(tool)
            
            allowed_count = sum(1 for t in tools if t.is_allowed)
            blocked_count = len(tools) - allowed_count
            
            self.tools_cache = tools
            logging.info(f"Loaded {allowed_count} allowed tools, blocked {blocked_count} tools from {self.name}")
            return tools
        except Exception as e:
            logging.error(f"Error getting tools from {self.name}: {e}")
            return []
    
    async def run_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        if not self.session:
            return "Error: Server not connected"
        
        try:
            response = await self.session.call_tool(tool_name, args)
            
            if response.isError:
                return f"Tool error: {response.content}"
            
            return response.content
        except Exception as e:
            logging.error(f"Error running tool {tool_name}: {e}")
            return f"Error: {str(e)}"
    
    async def stop(self) -> None:
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._http_context:
                await self._http_context.__aexit__(None, None, None)
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
        except Exception as e:
            logging.error(f"Error stopping server {self.name}: {e}")
