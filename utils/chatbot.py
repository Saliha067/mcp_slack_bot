"""ChatBot class for LLM interactions using LangChain."""
import logging
from typing import Dict, List

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


class ChatBot:
    """Simple LLM client for chat interactions"""
    def __init__(self, api_key: str, model: str, ollama_url: str):
        self.api_key = api_key
        self.model = model
        self.ollama_url = ollama_url
    
    async def get_response(self, messages: List[Dict[str, str]]) -> str:
        """Get a response from the LLM"""
        try:
            # Set up the right model
            if "gpt" in self.model.lower():
                llm = ChatOpenAI(
                    api_key=self.api_key,
                    model_name=self.model,
                    temperature=0.7
                )
            else:
                llm = ChatOllama(
                    model=self.model,
                    base_url=self.ollama_url,
                    temperature=0.1
                )
            
            # Convert messages to LangChain format
            chain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    chain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    chain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chain_messages.append(AIMessage(content=msg["content"]))
            
            # Get response
            response = await llm.ainvoke(chain_messages)
            if isinstance(response, (str, list, dict)):
                return str(response)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logging.error(f"Error getting LLM response: {e}")
            if "connection refused" in str(e).lower():
                return "Error: Could not connect to the AI model. Is it running?"
            return f"Sorry, there was an error: {str(e)}"
