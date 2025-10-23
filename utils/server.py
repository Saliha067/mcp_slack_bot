"""MCP Server connection handler supporting both stdio and HTTP protocols."""
import asyncio
import logging
import subprocess
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from .tool import Tool


class Server:
    """Handles MCP server connections with support for both stdio and HTTP"""
    def __init__(self, name: str, config: Dict, main_config=None):
        self.name = name
        self.config = config
        self.main_config = main_config
        self.session = None
        self._stack = None
        self._context = None
        self.is_http = "url" in config
    
    async def start(self) -> None:
        """Start the server based on its configuration"""
        try:
            if self.is_http:
                # Use streamablehttp_client for HTTP-based MCP servers
                client = streamablehttp_client(self.config["url"])
                self._stack = client
                self._context = await client.__aenter__()
                read, write, get_session_id = self._context  # HTTP returns 3 values
                
                session = ClientSession(read, write)
                self.session = session
                await session.__aenter__()
                await self.session.initialize()
            else:
                cmd = "npx" if self.config["command"] == "npx" else self.config["command"]
                
                params = StdioServerParameters(
                    command=cmd,
                    args=self.config["args"],
                    env=self.config.get("env")
                )
                
                client = stdio_client(params)
                self._stack = client
                self._context = await client.__aenter__()
                read, write = self._context  # stdio returns 2 values
                
                session = ClientSession(read, write)
                self.session = session
                await session.__aenter__()
                await self.session.initialize()
        except Exception as e:
            # Clean up on failure
            await self._cleanup_on_error()
            logging.error(f"Error starting server {self.name}: {e}")
            raise
    
    async def _cleanup_on_error(self) -> None:
        """Clean up resources when startup fails"""
        try:
            if self.session:
                try:
                    await self.session.__aexit__(None, None, None)
                except:
                    pass
                self.session = None
            
            if self._stack:
                try:
                    await self._stack.__aexit__(None, None, None)
                except:
                    pass
                self._stack = None
                self._context = None
        except:
            pass  # Suppress all errors during error cleanup

    async def stop(self) -> None:
        """Stop the server gracefully"""
        try:
            if self.session:
                try:
                    await self.session.__aexit__(None, None, None)
                except (Exception, asyncio.CancelledError):
                    pass
            if self._stack:
                try:
                    await self._stack.__aexit__(None, None, None)
                except (Exception, asyncio.CancelledError):
                    pass
        except (Exception, asyncio.CancelledError):
            pass
        finally:
            self.session = None
            self._stack = None
            self._context = None
    
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
                        # Pass the main_config if available, otherwise fall back to server config
                        config_to_use = self.main_config if self.main_config else self.config
                        tools.append(Tool(tool.name, tool.description, tool.inputSchema, config_to_use))
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
                except (Exception, asyncio.CancelledError):
                    pass
                self.session = None
                
            if self._stack:
                try:
                    await self._stack.__aexit__(None, None, None)
                except (Exception, asyncio.CancelledError):
                    pass
                self._stack = None
                self._context = None
                
        except (Exception, asyncio.CancelledError):
            pass
