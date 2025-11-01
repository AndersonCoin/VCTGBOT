"""
Main application entry point for Telegram Music Bot.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

import aiohttp
from aiohttp import web

from config import config
from bot.client import BotClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.app.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('music_bot.log')
    ]
)

logger = logging.getLogger(__name__)


async def health_check_handler(request):
    """Health check endpoint."""
    try:
        bot_client = request.app['bot_client']
        health = await bot_client.health_check()
        
        return web.json_response({
            "status": "ok",
            "bot_status": health,
            "timestamp": asyncio.get_event_loop().time()
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return web.json_response({
            "status": "error",
            "error": str(e)
        }, status=500)


async def index_handler(request):
    """Index endpoint."""
    return web.json_response({
        "message": "Telegram Music Bot is running!",
        "version": "2.1.0",
        "status": "active"
    })


async def start_health_server():
    """Start the health check server."""
    try:
        app = web.Application()
        
        # Add bot client reference
        # This will be set later when bot client is created
        app.router.add_get('/', index_handler)
        app.router.add_get('/health', health_check_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', config.app.port)
        await site.start()
        
        logger.info(f"Health check server started on port {config.app.port}")
        
        return runner
        
    except Exception as e:
        logger.error(f"Failed to start health server: {e}")
        raise


async def setup_signal_handlers(bot_client: BotClient):
    """Setup signal handlers for graceful shutdown."""
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(shutdown(bot_client))
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def shutdown(bot_client: BotClient):
    """Graceful shutdown handler."""
    logger.info("Starting graceful shutdown...")
    
    try:
        # Stop bot
        await bot_client.stop()
        
        logger.info("Bot stopped successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    finally:
        # Exit
        sys.exit(0)


async def cleanup_downloads(download_dir: Path):
    """Clean up old download files."""
    try:
        import time
        current_time = time.time()
        max_age_hours = 24
        
        for file_path in download_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > (max_age_hours * 3600):
                    try:
                        file_path.unlink()
                        logger.info(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to clean up {file_path}: {e}")
                        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


async def register_plugins(app, bot_client: BotClient):
    """Register all bot plugins."""
    try:
        # Import plugins
        from bot.plugins import start, play, controls, queue, callbacks
        
        # Register handlers
        start.register_handlers(app, bot_client)
        play.register_handlers(app, bot_client)
        controls.register_handlers(app, bot_client)
        queue.register_handlers(app, bot_client)
        callbacks.register_handlers(app, bot_client)
        
        logger.info("All plugins registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register plugins: {e}")
        raise


async def main():
    """Main application function."""
    try:
        logger.info("Starting Telegram Music Bot v2.1...")
        logger.info(config)
        
        # Validate configuration
        config.validate()
        
        # Create bot client
        bot_client = BotClient()
        
        # Setup signal handlers
        await setup_signal_handlers(bot_client)
        
        # Start health check server
        health_runner = await start_health_server()
        
        # Set bot client reference for health endpoint
        health_app = health_runner.app
        health_app['bot_client'] = bot_client
        
        # Register plugins
        await register_plugins(bot_client.bot, bot_client)
        
        # Start bot
        await bot_client.start()
        
        # Periodic cleanup
        async def periodic_cleanup():
            """Periodic cleanup of old files."""
            while True:
                try:
                    await asyncio.sleep(3600)  # Every hour
                    await cleanup_downloads(config.app.download_dir)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Periodic cleanup error: {e}")
        
        cleanup_task = asyncio.create_task(periodic_cleanup())
        
        logger.info("Bot is now running. Press Ctrl+C to stop.")
        
        # Keep the application running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            # Cleanup
            cleanup_task.cancel()
            await bot_client.stop()
            await health_runner.cleanup()
            
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    try:
        # Run the application
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
