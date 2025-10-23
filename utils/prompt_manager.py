"""Prompt management for MCP Slack Bot."""
import logging
import os
from typing import Dict, Optional

import yaml


class PromptManager:
    """Manages prompts with server-specific customization support"""
    
    def __init__(self, config_path: str = "prompts/prompts_config.yaml"):
        """Initialize prompt manager with YAML config file"""
        self.config_path = config_path
        self.config = self._load_config()
        self.defaults = self.config.get("defaults", {})
        self.server_prompts = self.config.get("server_prompts", {})
        self.thresholds = self.config.get("thresholds", {})
        self.parameter_hints = self.config.get("parameter_hints", {})
    
    def _load_config(self) -> Dict:
        """Load prompts configuration from YAML file"""
        try:
            # Get project root directory (parent of utils folder)
            project_root = os.path.dirname(os.path.dirname(__file__))
            config_file = os.path.join(project_root, self.config_path)
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            return config if config else {}
        except FileNotFoundError:
            logging.warning(f"Prompts config file {self.config_path} not found, using defaults")
            return self._get_fallback_config()
        except yaml.YAMLError as e:
            logging.error(f"Invalid YAML in {self.config_path}: {e}, using defaults")
            return self._get_fallback_config()
        except Exception as e:
            logging.error(f"Error loading prompts config: {e}, using defaults")
            return self._get_fallback_config()
    
    def _get_fallback_config(self) -> Dict:
        """Return minimal fallback config if file loading fails"""
        return {
            "defaults": {
                "system_intent_analysis": "You are an expert at analyzing user queries and determining which tool to use.",
                "system_interpret_result": "Analyze the data and present useful information.",
                "system_interpret_large": "Extract and present the most relevant information.",
                "user_interpret_result": 'User asked: "{user_query}"\n\nTool returned:\n{result}\n\nPresent the key information.',
                "user_interpret_large": 'User asked: "{user_query}"\n\nTool returned:\n{result}\n\nExtract the most useful information.'
            },
            "thresholds": {
                "large_response_chars": 2000
            },
            "server_prompts": {},
            "parameter_hints": {}
        }
    
    def get_system_intent_analysis_prompt(self, server_name: Optional[str] = None) -> str:
        """
        Get the system prompt for intent analysis (elicitation)
        
        Args:
            server_name: Name of the MCP server (for server-specific prompts)
        
        Returns:
            System prompt string
        """
        # Check for server-specific prompt first
        if server_name and server_name in self.server_prompts:
            server_config = self.server_prompts[server_name]
            if "system_intent_analysis" in server_config:
                return server_config["system_intent_analysis"]
        
        # Fall back to default prompt
        return self.defaults.get("system_intent_analysis", 
            "You are an expert at analyzing user queries and determining which tool to use.")
    
    def get_system_interpret_prompt(self, server_name: Optional[str] = None, is_large: bool = False) -> str:
        """
        Get system prompt for interpreting tool results
        
        Args:
            server_name: Name of the MCP server (for server-specific prompts)
            is_large: Whether the result is large (uses different prompt)
        
        Returns:
            System prompt string
        """
        # Check for server-specific prompt first
        if server_name and server_name in self.server_prompts:
            server_config = self.server_prompts[server_name]
            if "system_interpret_result" in server_config:
                return server_config["system_interpret_result"]
        
        # Fall back to default prompt
        if is_large:
            return self.defaults.get("system_interpret_large", "Extract and present relevant information.")
        else:
            return self.defaults.get("system_interpret_result", "Analyze and present useful information.")
    
    def get_user_interpret_prompt(
        self, 
        user_query: str, 
        tool_name: str, 
        result: str, 
        server_name: Optional[str] = None, 
        is_large: bool = False
    ) -> str:
        """
        Get user prompt for interpreting tool results with values filled in
        
        Args:
            user_query: The original user question
            tool_name: Name of the tool that was called
            result: The result returned by the tool
            server_name: Name of the MCP server (for server-specific prompts)
            is_large: Whether the result is large (uses different template)
        
        Returns:
            User prompt string with values filled in
        """
        # Check for server-specific prompt template first
        template = None
        if server_name and server_name in self.server_prompts:
            server_config = self.server_prompts[server_name]
            if "user_interpret_result" in server_config:
                template = server_config["user_interpret_result"]
        
        # Fall back to default template
        if not template:
            if is_large:
                template = self.defaults.get("user_interpret_large", "")
            else:
                template = self.defaults.get("user_interpret_result", "")
        
        # Fill in template values
        return template.format(
            user_query=user_query,
            tool_name=tool_name,
            result=result
        )
    
    def is_large_result(self, result: str) -> bool:
        """Check if a result is considered 'large' based on character count"""
        threshold = self.thresholds.get("large_response_chars", 2000)
        return len(result) > threshold
    
    def get_parameter_hints(self) -> Dict:
        """Get parameter extraction hints for query parsing"""
        return self.parameter_hints
    
    def get_threshold(self, name: str, default: int = 2000) -> int:
        """Get a specific threshold value"""
        return self.thresholds.get(name, default)
