"""
Dynamic prompt builder for infrastructure troubleshooting bot.

This module constructs system prompts by:
1. Loading domain-specific context from markdown files
2. Auto-generating tool lists from loaded LangChain tools
3. Categorizing tools by their source (MCP servers, local tools, etc.)
4. Including relevant examples and guidelines
"""

import os
from pathlib import Path
from typing import List
from langchain_core.tools import BaseTool


class PromptBuilder:
    """Build dynamic system prompts from modular components."""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        
    def load_file(self, filepath: str) -> str:
        """Load content from a markdown file."""
        full_path = self.prompts_dir / filepath
        if not full_path.exists():
            return f"<!-- File not found: {filepath} -->"
        return full_path.read_text()
    
    def generate_tool_list(self, tools: List[BaseTool]) -> str:
        """Generate formatted tool list from LangChain tools."""
        # Group tools by source
        retriever_tools = []
        math_tools = []
        mcp_tools = []
        other_tools = []
        
        for tool in tools:
            tool_name = tool.name.lower()
            tool_desc = tool.description.split('.')[0] if tool.description else ""
            tool_info = f"- **{tool.name}** - {tool_desc}"
            
            # Categorize by tool name patterns
            if tool.name == "search":
                retriever_tools.append(tool_info)
            elif any(name in tool_name for name in ["add_", "subtract_", "multiply_", "divide_"]):
                math_tools.append(tool_info)
            elif any(keyword in tool_name for keyword in [
                "query", "metric", "alert", "label", "series", "tsdb", 
                "export", "rule", "flag", "documentation", "prettify", 
                "explain", "relabel", "retention", "downsampling", "active_", "top_"
            ]):
                mcp_tools.append(tool_info)
            else:
                other_tools.append(tool_info)
        
        sections = []
        
        if retriever_tools:
            sections.append("### 1. Documentation Search:\n" + "\n".join(retriever_tools))
        
        if mcp_tools:
            sections.append("### 2. VictoriaMetrics MCP Tools:\n" + "\n".join(mcp_tools))
        
        if math_tools:
            sections.append("### 3. Math Tools (for calculations):\n" + "\n".join(math_tools))
        
        if other_tools:
            sections.append("### Other Tools (test fixtures, ignore in production):\n" + "\n".join(other_tools))
        
        return "\n\n".join(sections)
    
    def build_prompt(
        self,
        tools: List[BaseTool],
        domain_file: str = "domain.md",
        guidelines: List[str] = None,
        examples: List[str] = None
    ) -> str:
        """
        Build complete system prompt from components.
        
        Args:
            tools: List of LangChain tools to document
            domain_file: Path to domain definition (relative to prompts_dir)
            guidelines: List of guideline files to include (e.g., ["guidelines/response_rules.md"])
            examples: List of example files to include (e.g., ["examples/opensearch_latency.md"])
        
        Returns:
            Complete system prompt string
        """
        guidelines = guidelines or []
        examples = examples or []
        
        sections = []
        
        # 1. Domain definition
        sections.append(self.load_file(domain_file))
        
        # 2. Auto-generated tool list
        sections.append("## Available Tools:\n\n" + self.generate_tool_list(tools))
        
        # 3. Guidelines
        if guidelines:
            sections.append("## Guidelines:\n")
            for guideline in guidelines:
                sections.append(self.load_file(guideline))
        
        # 4. Examples
        if examples:
            sections.append("## Examples:\n")
            for example in examples:
                sections.append(self.load_file(example))
        
        return "\n\n".join(sections)
    
    def build_infrastructure_prompt(self, tools: List[BaseTool]) -> str:
        """Build minimal prompt for infrastructure troubleshooting."""
        return self.build_prompt(
            tools=tools,
            domain_file="domain.md",
            guidelines=[],  # No guidelines - domain.md is self-contained
            examples=[]      # No examples - keep prompt minimal
        )
