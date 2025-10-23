"""User elicitation handler for gathering missing or ambiguous information via MCP sampling."""
import logging
import inspect
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .tool import Tool


@dataclass
class ElicitationRequest:
    """Represents a request for user clarification"""
    tool_name: str
    missing_params: List[str]
    ambiguous_query: Optional[str]
    suggested_values: Optional[Dict[str, Any]]
    question: str
    

class ElicitationHandler:
    """
    Handles user elicitation for MCP tool calls.
    
    Uses PromptManager for configurable prompts and MCP's sampling capabilities
    to ask users for clarification when:
    - Required parameters are missing
    - User query is ambiguous
    - Additional confirmation is needed
    """
    
    def __init__(self, chat_bot, prompt_manager):
        """
        Initialize elicitation handler
        
        Args:
            chat_bot: ChatBot instance for LLM-based analysis
            prompt_manager: PromptManager instance for getting prompts
        """
        self.chat_bot = chat_bot
        self.prompt_manager = prompt_manager
        self.pending_requests: Dict[str, ElicitationRequest] = {}  # channel_id -> request
    
    async def analyze_user_intent(
        self, 
        user_query: str, 
        available_tools: List[Tool],
        conversation_history: List[Dict[str, str]] = None
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """
        Analyze user query to determine if we can execute a tool or need more info.
        
        Args:
            user_query: The user's natural language query
            available_tools: List of available tools
            conversation_history: Previous conversation context
            
        Returns:
            Tuple of (tool_name, arguments, clarification_question)
            - If clarification_question is not None, we need to ask the user
            - If tool_name and arguments are present, we can execute
            - If all are None, it's a conversational query
        """
        if not available_tools:
            return None, None, None
        
        # Create a specialized prompt for intent analysis
        tools_info = "\n".join([
            f"- {tool.name}: {tool.description}\n  Parameters: {tool.get_parameter_info()}"
            for tool in available_tools
        ])
        
        # Get system prompt from PromptManager
        base_prompt = self.prompt_manager.get_system_intent_analysis_prompt()
        system_prompt = f"""{base_prompt}

Available tools:
{tools_info}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User query: {user_query}"}
        ]
        
        # Log intent analysis
        logging.debug(f"Analyzing intent for: '{user_query}' ({len(available_tools)} tools available)")
        
        # Add conversation history if available
        if conversation_history:
            context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in conversation_history[-3:]
            ])
            messages.append({
                "role": "user", 
                "content": f"Previous context:\n{context}"
            })
        
        try:
            resp = self.chat_bot.get_response(messages)
            # Support both coroutine/awaitable returns and plain (synchronous) strings
            if inspect.isawaitable(resp):
                response = await resp
            else:
                response = resp

            # Log LLM decision
            logging.debug(f"LLM response for '{user_query}': {response[:100]}...")
            
            return self._parse_intent_response(response, available_tools, user_query)
            
        except Exception as e:
            logging.error(f"Error analyzing user intent: {e}")
            return None, None, None
    
    def _parse_intent_response(
        self, 
        response: str, 
        available_tools: List[Tool],
        user_query: str = ""
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """Parse the LLM's intent analysis response"""
        
        # Check if it's a greeting
        if "GREETING: true" in response or "GREETING:true" in response:
            return "GREETING", None, None
        
        # Check if it's conversational
        if "CONVERSATIONAL: true" in response or "CONVERSATIONAL:true" in response:
            return None, None, None
        
        # Check if clarification is needed
        if "CLARIFY:" in response:
            # Extract clarification question
            lines = response.split("\n")
            clarify_lines = [l for l in lines if l.startswith("CLARIFY:")]
            if not clarify_lines:
                # Fallback if CLARIFY: format not found properly
                logging.warning(f"CLARIFY: keyword found but couldn't parse line. Response: {response}")
                return None, None, None
            
            clarify_line = clarify_lines[0]
            question = clarify_line.replace("CLARIFY:", "").strip()
            
            # Extract tool name if present
            tool_name = None
            if "TOOL:" in response:
                tool_lines = [l for l in lines if l.startswith("TOOL:")]
                if tool_lines:
                    tool_name = tool_lines[0].replace("TOOL:", "").strip()
            
            return tool_name, None, question
        
        # Check if ready to execute
        if "TOOL:" in response and "ARGS:" in response:
            lines = response.split("\n")
            
            # Extract tool name
            tool_lines = [l for l in lines if l.startswith("TOOL:")]
            if not tool_lines:
                logging.warning(f"TOOL: keyword found but couldn't parse line. Response: {response}")
                return None, None, None
            
            tool_line = tool_lines[0]
            tool_name = tool_line.replace("TOOL:", "").strip()
            
            # Validate tool exists and is allowed
            if not any(t.name == tool_name for t in available_tools):
                return None, None, f"Sorry, I don't have access to a tool that can do that right now."
            
            # Extract arguments
            args_start = response.find("ARGS:") + 5
            args_str = response[args_start:].strip()
            
            # Find the JSON object
            import json
            import re
            json_match = re.search(r'\{[^{}]*\}', args_str)
            if json_match:
                try:
                    args = json.loads(json_match.group(0))
                    return tool_name, args, None
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse args JSON: {e}")
                    return None, None, "I had trouble parsing the parameters. Could you rephrase your request?"
            else:
                # No args provided, might be a tool that doesn't need args
                return tool_name, {}, None
        
        # Couldn't parse - treat as conversational
        return None, None, None
    
    async def validate_tool_call(
        self, 
        tool_name: str, 
        args: Dict[str, Any], 
        tool: Tool
    ) -> Optional[str]:
        """
        Validate if a tool call has all required parameters.
        
        Args:
            tool_name: Name of the tool to call
            args: Arguments provided
            tool: Tool object with schema
            
        Returns:
            Clarification question if validation fails, None if valid
        """
        # Get required parameters from schema
        required_params = tool.get_required_parameters()
        
        if not required_params:
            return None  # No required params
        
        # Check for missing parameters
        missing = [param for param in required_params if param not in args]
        
        if missing:
            param_descriptions = tool.get_parameter_descriptions()
            missing_info = []
            for param in missing:
                desc = param_descriptions.get(param, "No description")
                missing_info.append(f"- **{param}**: {desc}")
            
            question = f"To use the **{tool_name}** tool, I need the following information:\n\n" + "\n".join(missing_info)
            return question
        
        return None
    
    async def handle_clarification_response(
        self,
        channel_id: str,
        user_response: str,
        original_tool: str,
        available_tools: List[Tool],
        pending_request: Optional[ElicitationRequest] = None
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """
        Process user's response to a clarification request.
        
        Args:
            channel_id: Slack channel ID
            user_response: User's clarification response
            original_tool: The tool we were trying to call
            available_tools: List of available tools
            pending_request: The pending elicitation request with context
            
        Returns:
            Tuple of (tool_name, arguments, further_clarification)
        """
        # If the original tool was "unknown", re-analyze the user's response
        # to determine which tool they want
        if original_tool == "unknown":
            return await self.analyze_user_intent(user_response, available_tools)
        
        # Find the tool
        tool = next((t for t in available_tools if t.name == original_tool), None)
        if not tool:
            # Tool not found - re-analyze the response
            return await self.analyze_user_intent(user_response, available_tools)
        
        # Use LLM to extract parameters from the clarification response
        param_info = tool.get_parameter_info()
        
        # Build context from pending request if available
        context_info = ""
        if pending_request:
            original_query_text = ""
            if pending_request.ambiguous_query:
                original_query_text = f"\n- User's original query was: '{pending_request.ambiguous_query}'"
            
            context_info = f"""
CONTEXT:{original_query_text}
- We asked the user: "{pending_request.question}"
- User is now responding to that specific question
- The user's original intent was to use tool '{original_tool}'
"""
        
        system_prompt = f"""You are helping extract parameter values from a user's clarification response.
{context_info}
The user was asked to clarify their request for the tool '{original_tool}'.
Now they responded: "{user_response}"

Tool parameters needed:
{param_info}

IMPORTANT:
- Extract parameter values from the user's natural language response
- Consider the CONTEXT above - the user is answering the specific clarification question we asked
- Responses like "yes", "ok", "sure", "yes from Binance", "ETH", etc. are VALID answers to clarification questions
- If the user says "yes", "ok", "sure" without additional info, look at the clarification question for default values or suggestions (e.g., "Binance by default" means use "Binance")
- If the clarification question mentions a default value like "(Binance by default)" or "(e.g., Binance)", use that value when user says "yes"
- If the user chose one option from multiple choices, identify which tool they want
- Use the exact format and values expected by the tool's parameters
- Be smart about common abbreviations and variations in the user's language
- ONLY mark as CONVERSATIONAL if the user asks a completely different question (e.g., "what time is it?" or "tell me a joke")

Response format:

If you can extract all parameters:
TOOL: {original_tool}
ARGS: {{"param1": "value1", "param2": "value2"}}

If you need more information:
CLARIFY: What specific information do you still need?

If the user is choosing between different tools:
TOOL: correct_tool_name
ARGS: {{"param1": "value1"}}

If the user's response is unrelated to the tool (e.g., asking "what time is it?" when asked for a symbol):
CONVERSATIONAL: true

EXAMPLES:

Example 1 - Simple answer:
Clarification question: "What symbol do you want to look up?"
User clarification: "AAPL"
Response:
TOOL: get_symbol_info
ARGS: {{"symbol": "AAPL"}}

Example 2 - Affirmative answer with explicit value:
Clarification question: "Which topic do you want to use (e.g., orders)?"
User clarification: "yes, orders"
Response:
TOOL: send_message
ARGS: {{"topic": "orders"}}

Example 3 - Affirmative with default value:
Clarification question: "Do you want to use the default topic? (orders by default)"
User clarification: "yes"
Response:
TOOL: send_message
ARGS: {{"topic": "orders"}}

Example 4 - Simple affirmation:
Clarification question: "Should I use the main channel?"
User clarification: "ok"
Response:
TOOL: send_message
ARGS: {{"channel": "main"}}

Example 5 - Completely unrelated:
Clarification question: "What symbol do you want to look up?"
User clarification: "what time is it?"
Response:
CONVERSATIONAL: true
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original tool we're trying to use: {original_tool}\nUser's clarification response: {user_response}"}
        ]
        
        resp = self.chat_bot.get_response(messages)
        if inspect.isawaitable(resp):
            response = await resp
        else:
            response = resp

        # Parse the response
        result = self._parse_intent_response(response, available_tools)
        
        # Check if it's a conversational response (None, None, None)
        if result == (None, None, None):
            # User asked something unrelated during clarification
            # Return None, None, None to signal this should be treated as conversational
            return None, None, None
        
        # If parsing succeeded and returned a valid tool, return it
        if result[0]:  # tool_name is not None
            return result
        
        # If parsing failed, we couldn't extract the information needed
        # Ask the user to be more specific
        required_params = tool.get_required_parameters()
        if required_params:
            param_list = ", ".join(required_params)
            return None, None, f"I need more information. Please provide: {param_list}"
        
        # If no required params, something else went wrong
        return None, None, "I didn't understand. Could you please rephrase your response?"
    
    def create_elicitation_request(
        self,
        channel_id: str,
        tool_name: str,
        question: str,
        missing_params: List[str] = None,
        suggested_values: Dict[str, Any] = None,
        original_query: str = None
    ) -> ElicitationRequest:
        """
        Create and store an elicitation request for a channel.
        
        Args:
            channel_id: Slack channel ID
            tool_name: Tool requiring clarification
            question: Question to ask the user
            missing_params: List of missing parameter names
            suggested_values: Any suggested/partial values
            original_query: The user's original query that led to this clarification
            
        Returns:
            ElicitationRequest object
        """
        request = ElicitationRequest(
            tool_name=tool_name,
            missing_params=missing_params or [],
            ambiguous_query=original_query,
            suggested_values=suggested_values,
            question=question
        )
        
        self.pending_requests[channel_id] = request
        return request
    
    def has_pending_request(self, channel_id: str) -> bool:
        """Check if there's a pending elicitation request for a channel"""
        return channel_id in self.pending_requests
    
    def get_pending_request(self, channel_id: str) -> Optional[ElicitationRequest]:
        """Get pending elicitation request for a channel"""
        return self.pending_requests.get(channel_id)
    
    def clear_pending_request(self, channel_id: str) -> None:
        """Clear pending elicitation request for a channel"""
        if channel_id in self.pending_requests:
            del self.pending_requests[channel_id]

