import asyncio
import logging
import warnings

from utils.config import Config
from utils.server import Server
from utils.chatbot import ChatBot
from utils.slack_bot import SlackBot

logging.basicConfig(level=logging.INFO)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('mcp.client.streamable_http').setLevel(logging.WARNING)


async def shutdown(bot):
    print("\n🔄 Shutting down bot...")
    if not bot:
        return
    
    try:
        if hasattr(bot, 'client') and bot.client:
            try:
                await bot.client.close()
            except (Exception, asyncio.CancelledError):
                pass
        
        for server in getattr(bot, 'servers', []):
            if server.session:
                try:
                    await server.stop()
                except (Exception, asyncio.CancelledError):
                    pass
        
        print("✨ Shutdown complete!")
    except (Exception, asyncio.CancelledError):
        pass


async def main():
    bot = None
    try:
        config = Config()
        
        if not config.slack_bot_token or not config.slack_app_token:
            print("❌ Missing Slack tokens in .env file")
            return
        
        print("🔧 Setting up components...")
        
        # Show environment mode
        env_mode = config.environment.upper()
        if config.environment == "prod":
            print(f"🏭 Running in {env_mode} mode - HTTP/Streamable servers only")
        else:
            print(f"🔬 Running in {env_mode} mode - All server types allowed")
        
        if not config.servers:
            print("❌ No MCP servers configured")
            return
        
        print(f"📦 Found {len(config.servers)} MCP server(s):")
        for server in config.servers:
            print(f"   • {server.name} ({server.type}): {server.url}")

        if not config.openai_api_key:
            print("❌ Missing OpenAI API key in .env file")
            return
        
        chat_bot = ChatBot(config.openai_api_key, config.model, config.ollama_url)
        
        try:
            test_response = await chat_bot.get_response([{"role": "user", "content": "Hi"}])
            if "error" in test_response:
                print(f"❌ Could not connect to model: {test_response}")
                return
            print(f"✅ Connected to model '{config.model}'")
        except Exception as e:
            print(f"❌ Error connecting to model: {e}")
            return
        
        bot = SlackBot(config.slack_bot_token, config.slack_app_token, config.servers, chat_bot, config)
        
        print("🚀 Starting bot...")
        await bot.start()
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Received shutdown signal")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if bot:
            try:
                await shutdown(bot)
            except (Exception, asyncio.CancelledError):
                pass


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=ResourceWarning)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✨ Shutdown complete!")

