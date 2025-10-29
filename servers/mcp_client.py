import json
import asyncio
import httpx
import warnings
from urllib.parse import urlparse
from langchain.tools import tool
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model
from typing import Any, Dict, Optional
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Suppress asyncio cleanup warnings from MCP SDK
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Attempted to exit cancel scope.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*unhandled errors in a TaskGroup.*")

# Global registry to keep sessions alive
_active_sessions = {}

class MCPSession:
    """MCP session handler using official SDK."""
    def __init__(self, server_url):
        self.server_url = server_url
        self.session = None
        self._http_context = None
        self._session_context = None
    
    async def connect(self):
        """Initialize session with the server."""
        url = self.server_url
        
        # Pre-check: Test if server is reachable before creating MCP connection
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.get(base_url)
        except Exception as pre_check_error:
            return False
        
        try:
            # Use official MCP SDK
            self._http_context = streamablehttp_client(url)
            read_stream, write_stream, _ = await asyncio.wait_for(
                self._http_context.__aenter__(), 
                timeout=5.0
            )
            
            self._session_context = ClientSession(read_stream, write_stream)
            self.session = await asyncio.wait_for(
                self._session_context.__aenter__(),
                timeout=5.0
            )
            
            await asyncio.wait_for(self.session.initialize(), timeout=5.0)
            return True
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            return False
    
    async def call(self, method, params=None):
        """Make a call to the MCP server."""
        if not self.session:
            if not await self.connect():
                return None
        
        try:
            if method == "tools/list":
                response = await asyncio.wait_for(
                    self.session.list_tools(),
                    timeout=5.0
                )
                return {"result": {"tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    } for tool in response.tools
                ]}}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                response = await asyncio.wait_for(
                    self.session.call_tool(tool_name, arguments),
                    timeout=5.0
                )
                return {"result": {"content": response.content}}
            return None
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return None
    
    async def close(self):
        """Close the session."""
        try:
            if self._session_context:
                await asyncio.wait_for(
                    self._session_context.__aexit__(None, None, None),
                    timeout=2.0
                )
        except:
            pass
        try:
            if self._http_context:
                await asyncio.wait_for(
                    self._http_context.__aexit__(None, None, None),
                    timeout=2.0
                )
        except:
            pass

def load_servers_config():
    """Load servers configuration from JSON file."""
    try:
        with open("servers_config.json", "r") as f:
            config = json.load(f)
        return config.get("servers", [])
    except Exception as e:
        print(f"Error loading servers config: {e}")
        return []

async def get_mcp_tools_from_server(server_config):
    """Get tools from an MCP server. Returns empty list if server is down."""
    server_name = server_config.get("name")
    server_url = server_config.get("url")
    allowed_tools = server_config.get("allowedTools", [])
    
    print(f"Connecting to {server_name} at {server_url}...")
    
    try:
        # Create session with proper context management
        session = MCPSession(server_url)
        connected = await session.connect()
        
        if not connected:
            print(f"✗ {server_name} connection failed")
            return []
        
        result = await session.call("tools/list")
        
        if result:
            server_tools = result.get("result", {}).get("tools", [])
            print(f"✓ {server_name} is available with {len(server_tools)} tools")
            
            # Store session in global registry to keep it alive for tool calls
            _active_sessions[server_name] = session
            
            # Create LangChain tools for each allowed tool
            tools = []
            for tool_info in server_tools:
                tool_name = tool_info.get("name")
                if tool_name in allowed_tools:
                    tools.append(create_mcp_tool(server_name, session, tool_info))
            
            return tools
        else:
            print(f"✗ {server_name} did not respond properly")
            await session.close()
            return []
    except Exception as e:
        error_msg = str(e)[:100]
        print(f"✗ {server_name} is not available: {error_msg}")
        return []

def create_mcp_tool(server_name, session, tool_info):
    """Create a LangChain tool from MCP tool info."""
    tool_name = tool_info.get("name")
    tool_description = tool_info.get("description", f"Call {tool_name} tool")
    input_schema = tool_info.get("inputSchema", {})
    
    # Get server URL from the session
    server_url = session.server_url
    
    # Enhance description for crypto tools to guide LLM
    if "binance" in server_name.lower() or "crypto" in tool_description.lower():
        if "symbol" in input_schema.get("properties", {}):
            tool_description = tool_description + "\n\nIMPORTANT: For crypto symbols, use the full trading pair format like 'BTCUSDT', 'ETHUSDT', 'BNBUSDT', etc. Common conversions: BTC->BTCUSDT, ETH->ETHUSDT, BNB->BNBUSDT."
    
    # Create Pydantic model from JSON schema
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    
    # Build field definitions for Pydantic model
    field_definitions = {}
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "string")
        prop_desc = prop_info.get("description", "")
        
        # Map JSON schema types to Python types
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list
        }
        python_type = type_mapping.get(prop_type, str)
        
        # Make field optional if not required
        if prop_name in required:
            field_definitions[prop_name] = (python_type, Field(..., description=prop_desc))
        else:
            field_definitions[prop_name] = (Optional[python_type], Field(None, description=prop_desc))
    
    # Create dynamic Pydantic model
    if field_definitions:
        ArgsSchema = create_model(f"{tool_name}_args", **field_definitions)
    else:
        ArgsSchema = None
    
    def sync_wrapper(**kwargs):
        """Synchronous wrapper - creates fresh connection for each call."""
        import asyncio
        import threading
        
        async def call_tool():
            # Create a fresh session for this call
            fresh_session = MCPSession(server_url)
            try:
                connected = await fresh_session.connect()
                if not connected:
                    return f"Error: Could not connect to {server_name}"
                
                result = await fresh_session.call("tools/call", {
                    "name": tool_name,
                    "arguments": kwargs
                })
                
                if result:
                    tool_result = result.get("result", {})
                    content = tool_result.get("content", [])
                    if content and len(content) > 0:
                        first_content = content[0]
                        if isinstance(first_content, dict):
                            return first_content.get("text", str(first_content))
                        elif hasattr(first_content, 'text'):
                            return first_content.text
                        else:
                            return str(first_content)
                    return str(tool_result)
                else:
                    return f"Error calling {tool_name}: No response"
            except Exception as e:
                return f"Error calling {tool_name}: {str(e)}"
            finally:
                await fresh_session.close()
        
        # Check if we're in an event loop already
        try:
            loop = asyncio.get_running_loop()
            # We're in a running loop - use a thread
            result_container = []
            def run_in_thread():
                result_container.append(asyncio.run(call_tool()))
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join(timeout=30)
            return result_container[0] if result_container else "Error: No result"
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            return asyncio.run(call_tool())
    
    # Create StructuredTool with schema
    if ArgsSchema:
        return StructuredTool(
            name=tool_name,
            description=tool_description,
            func=sync_wrapper,
            args_schema=ArgsSchema
        )
    else:
        # Fallback to simple tool if no schema
        @tool
        def simple_wrapper(**kwargs):
            return sync_wrapper(**kwargs)
        simple_wrapper.name = tool_name
        simple_wrapper.description = tool_description
        return simple_wrapper

async def load_all_mcp_tools():
    """Load all MCP tools from configured servers."""
    import asyncio
    servers = load_servers_config()
    all_tools = []
    
    for server_config in servers:
        server_tools = await get_mcp_tools_from_server(server_config)
        all_tools.extend(server_tools)
    
    print(f"\nTotal MCP tools loaded: {len(all_tools)}")
    return all_tools
