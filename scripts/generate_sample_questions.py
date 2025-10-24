#!/usr/bin/env python3
"""
Generate Sample Questions for MCP Slack Bot
This script reads servers_config.json and generates example questions
based on available servers and their tools.
"""

import json
import os
import sys

# Sample questions database for different tool types
TOOL_QUESTIONS = {
    # VictoriaMetrics tools
    "query": [
        "What's the CPU usage on server1?",
        "Show me memory usage for all servers",
        "What are the current HTTP request rates?",
        "Query cpu_usage{host=\"server1\"}",
        "Show me the average CPU across all servers"
    ],
    "query_range": [
        "Show me CPU usage trends for the last hour",
        "What was the memory usage pattern yesterday?",
        "Display HTTP request rate over the last 24 hours",
        "Show me disk usage trends for server1"
    ],
    "metrics": [
        "List all available metrics",
        "What metrics do we have in VictoriaMetrics?",
        "Show me all metric names",
        "What can I query in VictoriaMetrics?"
    ],
    "labels": [
        "What labels are available?",
        "Show me all label names",
        "List all tags in the metrics"
    ],
    "label_values": [
        "What are the values for host label?",
        "Show me all environments",
        "List all service names"
    ],
    "series": [
        "Show me all time series",
        "What series exist for cpu_usage?",
        "List all metric series"
    ],
    "documentation": [
        "How do I use VictoriaMetrics?",
        "Show me VictoriaMetrics documentation",
        "Help me with MetricsQL queries"
    ],
    
    # Binance tools
    "get_price": [
        "What's the current Bitcoin price?",
        "Show me BTC/USDT price",
        "What's the Ethereum price?",
        "Get price for BTCUSDT",
        "What's the current crypto market looking like?"
    ],
    "get_symbol_info": [
        "Give me information about BTCUSDT",
        "What are the trading details for Ethereum?",
        "Show me symbol info for BTC/USDT",
        "What's the trading pair information for Bitcoin?"
    ],
    
    # Generic/combined queries
    "combined": [
        "What's the Bitcoin price and CPU usage on server1?",
        "Show me crypto prices and system metrics",
        "Get BTC price and list all available metrics"
    ]
}

# Server-specific descriptions
SERVER_DESCRIPTIONS = {
    "VictoriaMetrics": "Time-series metrics database for monitoring and observability",
    "Binance": "Cryptocurrency exchange data and prices",
    "LocalFilesystem": "Local file system operations"
}

def load_config():
    """Load servers_config.json"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "servers_config.json"
    )
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        sys.exit(1)

def generate_questions(config):
    """Generate sample questions based on configuration"""
    
    print("=" * 80)
    print("📋 SAMPLE QUESTIONS FOR MCP SLACK BOT")
    print("=" * 80)
    print()
    
    servers = config.get("servers", [])
    
    if not servers:
        print("⚠️  No servers configured in servers_config.json")
        return
    
    print(f"🔧 Found {len(servers)} configured server(s)\n")
    
    # Questions by server
    for server in servers:
        name = server.get("name", "Unknown")
        server_type = server.get("type", "unknown")
        url = server.get("url", "N/A")
        allowed_tools = server.get("allowedTools", [])
        
        print(f"{'=' * 80}")
        print(f"🖥️  SERVER: {name}")
        print(f"{'=' * 80}")
        
        if name in SERVER_DESCRIPTIONS:
            print(f"📝 {SERVER_DESCRIPTIONS[name]}")
        
        print(f"🔗 Type: {server_type}")
        print(f"🌐 URL: {url}")
        print(f"🛠️  Tools: {len(allowed_tools) if allowed_tools else 'All tools allowed'}")
        print()
        
        if not allowed_tools:
            print("⚠️  No tools specified - all tools from this server will be available")
            print()
            continue
        
        # Generate questions for each tool
        for tool in allowed_tools:
            questions = TOOL_QUESTIONS.get(tool, [])
            
            if questions:
                print(f"  🔧 Tool: {tool}")
                print(f"  {'─' * 76}")
                for i, question in enumerate(questions, 1):
                    print(f"     {i}. {question}")
                print()
    
    # Combined queries
    if len(servers) > 1:
        print(f"{'=' * 80}")
        print(f"🔀 MULTI-SERVER QUERIES")
        print(f"{'=' * 80}")
        print("These queries use tools from multiple servers:\n")
        
        for i, question in enumerate(TOOL_QUESTIONS["combined"], 1):
            print(f"  {i}. {question}")
        print()
    
    # Testing queries for blocked tools
    print(f"{'=' * 80}")
    print(f"🚫 TEST BLOCKED TOOLS (Should be denied)")
    print(f"{'=' * 80}")
    print("Try these to test that tool filtering is working:\n")
    
    blocked_examples = [
        ("active_queries", "Show me the active queries in VictoriaMetrics"),
        ("alerts", "What are the current alerts?"),
        ("flags", "Show me VictoriaMetrics flags"),
        ("tsdb_status", "What's the TSDB cardinality status?"),
    ]
    
    for tool, question in blocked_examples:
        # Check if this tool is actually blocked (not in any allowedTools)
        is_blocked = True
        for server in servers:
            if tool in server.get("allowedTools", []):
                is_blocked = False
                break
        
        if is_blocked:
            print(f"  ❌ {question}")
            print(f"     (tries to use blocked tool: {tool})")
            print()
    
    # Quick start guide
    print(f"{'=' * 80}")
    print(f"🚀 QUICK START")
    print(f"{'=' * 80}")
    print("""
1. Make sure your bot is running:
   python main.py

2. In Slack, mention your bot or send a direct message:
   @your-bot What's the Bitcoin price?

3. Check the logs to see:
   • Tool filtering (allowed vs blocked)
   • Tool execution details
   • Results returned

4. Try the sample questions above to test different tools!
""")
    
    print(f"{'=' * 80}")
    print(f"💡 TIPS")
    print(f"{'=' * 80}")
    print("""
• Natural language works! The bot uses LLM for intent analysis
• You can ask follow-up questions in the same conversation
• Mix and match queries across different servers
• Check logs with: tail -f your-log-file.log
""")

def main():
    """Main entry point"""
    config = load_config()
    generate_questions(config)

if __name__ == "__main__":
    main()
