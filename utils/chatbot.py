import logging
from typing import Dict, List

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


class ChatBot:
    def __init__(self, api_key: str, model: str, ollama_url: str):
        self.api_key = api_key
        self.model = model
        self.ollama_url = ollama_url
    
    async def get_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            if "gpt" in self.model.lower():
                llm = ChatOpenAI(api_key=self.api_key, model_name=self.model, temperature=0.7)
            else:
                llm = ChatOllama(model=self.model, base_url=self.ollama_url, temperature=0.1)
            
            chain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    chain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    chain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chain_messages.append(AIMessage(content=msg["content"]))
            
            response = await llm.ainvoke(chain_messages)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logging.error(f"Error: {e}")
            return f"Error: {str(e)}"
