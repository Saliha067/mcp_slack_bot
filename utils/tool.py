"""MCP Tool representation with access control."""
from typing import Dict, Optional


class Tool:
    """Tool class for handling MCP tools with access control"""
    def __init__(self, name: str, description: str, input_schema: Dict, config, is_allowed: Optional[bool] = None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.config = config
        # Optional explicit override used in tests or programmatic tool creation
        self._is_allowed_override = is_allowed
    
    @property
    def is_allowed(self) -> bool:
        """Check if the tool is allowed based on configuration"""
        # If an explicit override was provided, respect it
        if self._is_allowed_override is not None:
            return bool(self._is_allowed_override)

        return not self.config.allowed_tools or self.name in self.config.allowed_tools
    
    def format_description(self) -> str:
        """Format tool description for the LLM if tool is allowed"""
        if not self.is_allowed:
            return ""
            
        args = []
        required_args = []
        optional_args = []
        
        if "properties" in self.input_schema:
            for name, info in self.input_schema["properties"].items():
                arg_type = info.get('type', 'string')
                arg_desc = info.get('description', 'No description')
                
                # Create example value based on type
                example = self._get_example_value(name, arg_type, arg_desc)
                
                arg_line = f"  - {name} ({arg_type}): {arg_desc}"
                
                if name in self.input_schema.get("required", []):
                    arg_line += " [REQUIRED]"
                    required_args.append((name, example))
                else:
                    arg_line += " [OPTIONAL]"
                    optional_args.append((name, example))
                
                args.append(arg_line)
        
        # Build example tool call
        example_params = {name: value for name, value in required_args[:3]}  # Show up to 3 params
        example_json = self._format_json_params(example_params)
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOL: {self.name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: {self.description}

PARAMETERS:
{chr(10).join(args) if args else '  (no parameters required)'}

USAGE EXAMPLE:
[{self.name}]
{example_json}

USE THIS TOOL WHEN: User asks about {self._extract_keywords(self.description)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    def _get_example_value(self, param_name: str, param_type: str, description: str):
        """Generate example value based on parameter info"""
        # Extract examples from description if present
        if 'e.g.' in description.lower():
            import re
            match = re.search(r'e\.g\.?\s*["\']?([^"\')\n]+)["\']?', description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Check parameter name for hints
        param_lower = param_name.lower()
        if 'timezone' in param_lower or 'zone' in param_lower:
            return "America/New_York"
        elif 'query' in param_lower or 'search' in param_lower:
            return "search term"
        elif 'index' in param_lower:
            return "logs-*"
        elif 'dashboard' in param_lower:
            return "dashboard-id"
        elif 'topic' in param_lower:
            return "topic-name"
        elif 'date' in param_lower or 'time' in param_lower:
            return "2025-10-22"
        elif 'id' in param_lower:
            return "12345"
        elif 'name' in param_lower:
            return "example-name"
        elif 'url' in param_lower:
            return "https://example.com"
        
        # Default by type
        if param_type == 'string':
            return "value"
        elif param_type == 'number' or param_type == 'integer':
            return 100
        elif param_type == 'boolean':
            return True
        elif param_type == 'array':
            return ["item1", "item2"]
        else:
            return "value"
    
    def _format_json_params(self, params: Dict) -> str:
        """Format parameters as JSON string"""
        import json
        if not params:
            return "{}"
        return json.dumps(params, indent=2)
    
    def _extract_keywords(self, description: str) -> str:
        """Extract key action words from description"""
        # Common words to highlight what the tool does
        keywords = []
        desc_lower = description.lower()
        
        # Action keywords
        actions = ['get', 'fetch', 'retrieve', 'search', 'query', 'find', 'list', 'show', 
                  'create', 'update', 'delete', 'send', 'post', 'publish', 'subscribe']
        
        for action in actions:
            if action in desc_lower:
                keywords.append(action)
        
        # Extract specific nouns (simple heuristic: capitalized words or quoted words)
        import re
        quoted = re.findall(r'["\']([^"\']+)["\']', description)
        keywords.extend(quoted)
        
        if keywords:
            return ', '.join(keywords[:5])  # Limit to 5 keywords
        return description[:50]  # Fallback to first 50 chars
    
    def get_required_parameters(self) -> list:
        """Get list of required parameter names"""
        return self.input_schema.get("required", [])
    
    def get_parameter_descriptions(self) -> Dict[str, str]:
        """Get dictionary of parameter names to descriptions"""
        descriptions = {}
        if "properties" in self.input_schema:
            for name, info in self.input_schema["properties"].items():
                descriptions[name] = info.get('description', 'No description available')
        return descriptions
    
    def get_parameter_info(self) -> str:
        """Get formatted string of all parameter information"""
        if "properties" not in self.input_schema:
            return "No parameters required"
        
        lines = []
        required = self.input_schema.get("required", [])
        
        for name, info in self.input_schema["properties"].items():
            param_type = info.get('type', 'string')
            desc = info.get('description', 'No description')
            req_marker = " (REQUIRED)" if name in required else " (optional)"
            lines.append(f"  • {name} ({param_type}){req_marker}: {desc}")
        
        return "\n".join(lines)

