import json
import logging
import os
from typing import Dict, List

from dotenv import load_dotenv
from utils.server import Server


class Config:
    def __init__(self):
        load_dotenv()
        
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "llama2")
        self.environment = os.getenv("ENVIRONMENT", "dev")  # prod or dev
        
        config = self._load_config()
        self.servers: List[Server] = self._create_servers(config.get("servers", []))
    
    def _load_config(self) -> Dict:
        try:
            project_root = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(project_root, "servers_config.json")
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return {}
    
    def _create_servers(self, servers_config: List[Dict]) -> List[Server]:
        servers = []
        for server_cfg in servers_config:
            try:
                server_type = server_cfg.get("type", "http")
                
                # Filter based on environment
                if self.environment == "prod" and server_type != "http":
                    logging.info(f"⚠️  Skipping {server_cfg.get('name')} ({server_type}) in prod mode - only HTTP servers allowed")
                    continue
                
                server_config = {
                    "url": server_cfg.get("url", ""),
                    "type": server_type,
                }
                
                server = Server(
                    name=server_cfg.get("name", "unknown"),
                    config=server_config,
                    app_config=self
                )
                
                server.allowed_tools = server_cfg.get("allowedTools", [])
                server.type = server_type
                server.url = server_cfg.get("url", "")
                
                servers.append(server)
                logging.info(f"✅ Loaded {server_cfg.get('name')} ({server_type}) server")
            except Exception as e:
                logging.error(f"Error creating server {server_cfg.get('name')}: {e}")
        return servers


