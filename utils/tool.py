from typing import Dict, Optional


class Tool:
    def __init__(self, name: str, description: str, input_schema: Dict, config, is_allowed: Optional[bool] = None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.config = config
        self._is_allowed = is_allowed
    
    @property
    def is_allowed(self) -> bool:
        if self._is_allowed is not None:
            return bool(self._is_allowed)
        return not self.config.allowed_tools or self.name in self.config.allowed_tools
    
    def get_required_parameters(self) -> list:
        return self.input_schema.get("required", [])
    
    def get_parameter_descriptions(self) -> Dict[str, str]:
        if "properties" not in self.input_schema:
            return {}
        return {name: info.get('description', '') for name, info in self.input_schema["properties"].items()}
    
    def get_parameter_info(self) -> str:
        if "properties" not in self.input_schema:
            return "No parameters"
        
        lines = []
        required = self.input_schema.get("required", [])
        for name, info in self.input_schema["properties"].items():
            param_type = info.get('type', 'string')
            desc = info.get('description', '')
            marker = "(required)" if name in required else ""
            lines.append(f"  • {name} ({param_type}) {marker}: {desc}".strip())
        
        return "\n".join(lines)

