"""Configuration management for the MCP Slack bot."""
import json
import logging
import os
from typing import Dict

from dotenv import load_dotenv


class Config:
    """Configuration class for the bot with environment support"""
    def __init__(self):
        load_dotenv()
        
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.environment = os.getenv("ENVIRONMENT", "prod")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "llama2")
        
        # Load server config to get allowed tools and MCP servers
        config = self.load_config()
        if not config:
            logging.error("Failed to load server configuration")
            self.allowed_tools = set()
            self.server_config = {}
        else:
            self.allowed_tools = set(config.get("allowedTools", []))
            self.server_config = config.get("mcpServers", {})
            if not self.server_config:
                logging.error("No MCP servers found in configuration")
    
    def load_config(self) -> Dict:
        """Load configuration from servers_config.json"""
        try:
            # Get project root directory (parent of utils folder)
            project_root = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(project_root, "servers_config.json")
            with open(config_path, "r") as f:
                config = json.load(f)
            if not isinstance(config, dict):
                logging.error("Invalid configuration format: expected JSON object")
                return {}
            return config
        except FileNotFoundError:
            logging.error("servers_config.json not found")
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in servers_config.json: {e}")
            return {}
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return {}
    
    def load_servers(self) -> Dict:
        """Load and filter server configuration based on environment"""
        if self.environment == "dev":
            return {
                name: server_config
                for name, server_config in self.server_config.items()
                if server_config.get("command") in ["docker", "npx"] or "url" in server_config
            }
        elif self.environment == "prod":
            return {
                name: server_config
                for name, server_config in self.server_config.items()
                if "url" in server_config
            }
        return self.server_config
