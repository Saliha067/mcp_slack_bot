import asyncio
import logging
import warnings

from utils.config import Config
from utils.server import Server
from utils.chatbot import ChatBot
from utils.slackbot import SlackBot

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Suppress verbose logging from libraries
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('mcp.client.streamable_http').setLevel(logging.WARNING)

async def shutdown(bot):
    """Gracefully shutdown the bot and cleanup resources"""
    print("\n🔄 Shutting down bot...")
    
    if not bot:
        return
    
    try:
        # Close Slack client session
        if hasattr(bot, 'client') and bot.client:
            try:
                await bot.client.close()
            except (Exception, asyncio.CancelledError):
                pass
        
        # Cleanup MCP servers
        for server in getattr(bot, 'servers', []):
            if server.session:  # Only clean up servers that were successfully started
                try:
                    await server.stop()
                except (Exception, asyncio.CancelledError):
                    pass  # Suppress all errors during shutdown
        
        print("✨ Shutdown complete!")
        
    except (Exception, asyncio.CancelledError):
        pass  # Suppress all errors during shutdown

def setup_signal_handlers(bot):
    """Set up signal handlers for graceful shutdown"""
    import signal
    
    def handle_signal(signum, frame):
        print(f"\n⚡ Received signal {signal.Signals(signum).name}")
        asyncio.create_task(shutdown(bot))
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

async def main():
    """Main function to run the bot"""
    bot = None
    try:
        config = Config()
        
        if not config.slack_bot_token or not config.slack_app_token:
            print("❌ Error: Missing Slack tokens in .env file")
            return
        
        # Set up components
        print("🔧 Setting up components...")
        server_config = config.load_servers()
        if not server_config:
            print("❌ Error: No server configuration available")
            return
            
        servers = [Server(name, cfg, config) for name, cfg in server_config.items()]

        if not config.openai_api_key:
            print("❌ Error: Missing OpenAI API key in .env file")
            return
        
        # Test connectivity to local model
        try:
            test_bot = ChatBot(config.openai_api_key, config.model, config.ollama_url)
            test_response = await test_bot.get_response([{"role": "user", "content": "Hello"}])
            if "error" in test_response:
                print(f"❌ Error: Could not connect to local model: {test_response}")
                return
            print(f"✅ Connected to local model '{config.model}' successfully")
        except Exception as e:
            print(f"❌ Error connecting to local model: {e}")
            return
            
        chat_bot = ChatBot(config.openai_api_key, config.model, config.ollama_url)
        
        # Create and start bot
        bot = SlackBot(config.slack_bot_token, config.slack_app_token, servers, chat_bot, config)
        
        print("🚀 Starting bot...")
        await bot.start()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Received shutdown signal (Ctrl+C)")
    except asyncio.CancelledError:
        # Handle cancellation gracefully
        pass
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if bot:
            try:
                await shutdown(bot)
            except (Exception, asyncio.CancelledError):
                # Suppress all errors during final shutdown
                pass

if __name__ == "__main__":
    # Suppress asyncio warnings about unclosed resources during shutdown
    warnings.filterwarnings("ignore", category=ResourceWarning)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This catches Ctrl+C during asyncio.run()
        print("\n✨ Shutdown complete!")
        pass
