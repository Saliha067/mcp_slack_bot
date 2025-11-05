"""
Response formatter for Slack messages using Block Kit.
Supports clean, structured formatting for both Ollama and OpenAI responses.
"""

from typing import List, Dict, Any, Optional
import re


class SlackResponseFormatter:
    """
    Formats AI responses into clean, structured Slack Block Kit messages.
    Minimal emoji usage, focused on readability and clarity.
    """
    
    @staticmethod
    def format_help_message(tools: List[Any]) -> Dict[str, Any]:
        """
        Format help message listing available tools.
        
        Args:
            tools: List of tool objects with name and description attributes
            
        Returns:
            Slack blocks payload
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Available Tools"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Group tools by category
        tool_categories = {
            "Company Information": [],
            "Mathematics": [],
            "MCP Tools": [],
            "Other": []
        }
        
        for tool in tools:
            tool_name = tool.name
            # Get first meaningful line of description
            lines = tool.description.strip().split('\n')
            tool_desc = lines[0].strip() if lines else "No description"
            # If first line is too short, try to get more context
            if len(tool_desc) < 20 and len(lines) > 1:
                tool_desc = lines[1].strip()
            # Truncate if too long
            if len(tool_desc) > 100:
                tool_desc = tool_desc[:97] + "..."
            
            # Categorize tools
            if tool_name == "search":
                tool_categories["Company Information"].append((tool_name, tool_desc))
            elif "number" in tool_name or "math" in tool_name.lower():
                tool_categories["Mathematics"].append((tool_name, tool_desc))
            elif tool_name not in ["search"] and ("get_" in tool_name or "fetch_" in tool_name):
                tool_categories["MCP Tools"].append((tool_name, tool_desc))
            else:
                tool_categories["Other"].append((tool_name, tool_desc))
        
        # Add tools by category
        for category, category_tools in tool_categories.items():
            if not category_tools:
                continue
                
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{category}*"
                }
            })
            
            for tool_name, tool_desc in category_tools:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• `{tool_name}` — {tool_desc}"
                    }
                })
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Mention me with your question to use these tools_"
                }
            ]
        })
        
        # Include fallback text for accessibility
        tool_names = [tool.name for tool in tools]
        fallback_text = f"Available Tools: {', '.join(tool_names)}"
        
        return {"blocks": blocks, "text": fallback_text}
    
    @staticmethod
    def format_agent_response(
        response_text: str,
        tools_used: Optional[List[str]] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Format agent response into clean Slack blocks.
        
        Args:
            response_text: The AI-generated response text
            tools_used: Optional list of tool names that were invoked
            include_metadata: Whether to include metadata section
            
        Returns:
            Slack blocks payload
        """
        blocks = []
        
        # Parse and structure the response
        sections = SlackResponseFormatter._parse_response_sections(response_text)
        
        # Add main content
        if len(sections) == 1:
            # Single section response
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": SlackResponseFormatter._format_text(sections[0])
                }
            })
        else:
            # Multi-section response
            for i, section in enumerate(sections):
                if i > 0:
                    blocks.append({"type": "divider"})
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": SlackResponseFormatter._format_text(section)
                    }
                })
        
        # Add metadata footer if tools were used
        if include_metadata and tools_used:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Tools used: {' • '.join(f'`{t}`' for t in tools_used)}"
                    }
                ]
            })
        
        # Generate fallback text (strip markdown for accessibility)
        fallback_text = response_text[:500]  # Limit to 500 chars for fallback
        if len(response_text) > 500:
            fallback_text += "..."
        
        return {"blocks": blocks, "text": fallback_text}
    
    @staticmethod
    def format_error_message(error_msg: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Format error message with clear structure.
        
        Args:
            error_msg: The error message to display
            context: Optional context about what went wrong
            
        Returns:
            Slack blocks payload
        """
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Error*\n{error_msg}"
                }
            }
        ]
        
        if context:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_{context}_"
                    }
                ]
            })
        
        # Fallback text for accessibility
        fallback_text = f"Error: {error_msg}"
        
        return {"blocks": blocks, "text": fallback_text}
    
    @staticmethod
    def _parse_response_sections(text: str) -> List[str]:
        """
        Parse response text into logical sections.
        Handles numbered lists, bullet points, and paragraph breaks.
        """
        # Split by double newlines for major sections
        paragraphs = text.split('\n\n')
        
        # Clean up and filter empty sections
        sections = [p.strip() for p in paragraphs if p.strip()]
        
        # If only one section or very short, return as-is
        if len(sections) <= 1 or len(text) < 200:
            return [text.strip()]
        
        return sections
    
    @staticmethod
    def _format_text(text: str) -> str:
        """
        Format text with proper Markdown for Slack.
        Converts common patterns to Slack-friendly format.
        """
        # Convert bold patterns
        text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
        
        # Convert code blocks (preserve existing)
        # Already handled by Slack
        
        # Format lists properly
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Handle bullet points
            if stripped.startswith('- ') or stripped.startswith('• '):
                formatted_lines.append(f"  • {stripped[2:]}")
            # Handle numbered lists
            elif re.match(r'^\d+\.', stripped):
                formatted_lines.append(f"  {stripped}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    @staticmethod
    def format_simple_text(text: str) -> Dict[str, Any]:
        """
        Format simple text response without complex structure.
        Use this for quick replies.
        
        Args:
            text: The text to format
            
        Returns:
            Slack message payload (text-only for simplicity)
        """
        return {"text": text}
    
    @staticmethod
    def should_use_blocks(text: str) -> bool:
        """
        Determine if response should use Block Kit or plain text.
        
        Args:
            text: The response text
            
        Returns:
            True if blocks should be used, False for plain text
        """
        # Use blocks if:
        # - Response is longer than 200 chars
        # - Contains multiple paragraphs
        # - Contains lists
        # - Contains code blocks
        
        if len(text) > 200:
            return True
        if '\n\n' in text:
            return True
        if re.search(r'^\s*[-•\d+\.]\s+', text, re.MULTILINE):
            return True
        if '```' in text:
            return True
        
        return False
