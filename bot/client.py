"""
Bot client initialization and management.
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional

from pyrogram import Client as PyrogramClient
from pyrogram.errors import ApiIdInvalid, ApiIdPublishedFlood
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import UnAuthorized

from config import config
from bot.core.player import Player
from bot.core.queue import QueueManager
from bot.helpers.localization import Localization
from bot.helpers.youtube import YouTubeHelper
from bot.helpers.assistant import AssistantManager
from bot.helpers.keyboards import KeyboardBuilder
from bot.helpers.formatting import Formatter
from bot.persistence.state import StateManager
from bot.persistence.storage import create_storage_backend


class BotClient:
    """Main bot client with all components."""
    
    def __init__(self):
        """Initialize bot client."""
        self.bot: Optional[PyrogramClient] = None
        self.assistant: Optional[PyrogramClient] = None
        self.pytgcalls: Optional[PyTgCalls] = None
        self.player: Optional[Player] = None
        self.queue_manager: Optional[QueueManager] = None
        self.localization: Optional[Localization] = None
        self.youtube: Optional[YouTubeHelper] = None
        self.assistant_manager: Optional[AssistantManager] = None
        self.keyboards: Optional[KeyboardBuilder] = None
        self.formatter: Optional[Formatter] = None
        self.state_manager: Optional[StateManager] = None
        
        self.logger = logging.getLogger(__name__)
        self.is_running = False
    
    async def initialize(self):
        """Initialize all bot components."""
        try:
            self.logger.info("Initializing bot components...")
            
            # Initialize storage backend
            storage_backend = create_storage_backend(
                config.database.backend,
                config.app.download_dir / "state.db"
            )
            
            # Initialize localization
            self.localization = Localization()
            
            # Initialize YouTube helper
            self.youtube = YouTubeHelper(config.app.download_dir)
            
            # Initialize utilities
            self.keyboards = KeyboardBuilder()
            self.formatter = Formatter()
            
            # Initialize Pyrogram clients
            await self._initialize_clients()
            
            # Initialize PyTgCalls
            await self._initialize_pytgcalls()
            
            # Initialize core components
            self.player = Player(self.pytgcalls)
            self.queue_manager = QueueManager()
            
            # Initialize assistant manager
            self.assistant_manager = AssistantManager(
                config.bot.assistant_username,
                self.bot,
                self.assistant
            )
            
            # Initialize state manager
            self.state_manager = StateManager(storage_backend)
            
            # Register event handlers
            self._register_handlers()
            
            self.logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def _initialize_clients(self):
        """Initialize Pyrogram clients."""
        try:
            # Initialize bot client
            self.bot = PyrogramClient(
                "bot",
                api_id=config.bot.api_id,
                api_hash=config.bot.api_hash,
                bot_token=config.bot.bot_token,
                workdir=config.app.download_dir
            )
            
            # Initialize assistant client using session string
            self.assistant = PyrogramClient(
                "assistant",
                api_id=config.bot.api_id,
                api_hash=config.bot.api_hash,
                session_string=config.bot.session_string,
                workdir=config.app.download_dir
            )
            
            # Start clients
            self.logger.info("Starting Pyrogram clients...")
            await self.bot.start()
            await self.assistant.start()
            
            # Verify bot token
            bot_me = await self.bot.get_me()
            self.logger.info(f"Bot started: @{bot_me.username} ({bot_me.id})")
            
            # Verify assistant session
            assistant_me = await self.assistant.get_me()
            self.logger.info(f"Assistant started: @{assistant_me.username} ({assistant_me.id})")
            
        except ApiIdInvalid:
            self.logger.error("Invalid API ID or API Hash")
            raise
        except ApiIdPublishedFlood:
            self.logger.error("API ID is published in flood")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            raise
    
    async def _initialize_pytgcalls(self):
        """Initialize PyTgCalls."""
        try:
            self.logger.info("Initializing PyTgCalls...")
            
            self.pytgcalls = PyTgCalls(
                self.assistant,
                log_mode="INFO"
            )
            
            await self.pytgcalls.start()
            self.logger.info("PyTgCalls started successfully")
            
        except UnAuthorized:
            self.logger.error("Unauthorized access - check session string")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize PyTgCalls: {e}")
            raise
    
    def _register_handlers(self):
        """Register event handlers."""
        if self.player:
            self.player.register_handlers(on_stream_end=self._on_stream_end)
    
    async def _on_stream_end(self, chat_id: int):
        """Handle stream end event."""
        try:
            self.logger.info(f"Stream ended for chat {chat_id}, getting next track...")
            
            # Auto-play next track
            next_track = self.queue_manager.auto_next(chat_id)
            
            if next_track and self.player:
                # Start next track
                success = await self.player.play_audio(
                    chat_id, 
                    next_track.file_path
                )
                
                if success:
                    # Update now playing message
                    await self._update_now_playing_message(chat_id)
                else:
                    self.logger.error(f"Failed to start next track for chat {chat_id}")
            else:
                self.logger.info(f"No more tracks for chat {chat_id}")
                # Stop progress updater
                if self.player:
                    await self.player.stop_progress_updater(chat_id)
                
        except Exception as e:
            self.logger.error(f"Error handling stream end for chat {chat_id}: {e}")
    
    async def _update_now_playing_message(self, chat_id: int):
        """Update now playing message."""
        try:
            if not self.player or not self.localization:
                return
            
            current_track = self.queue_manager.get_current_track(chat_id)
            if not current_track:
                return
            
            # Get chat info
            chat = await self.bot.get_chat(chat_id)
            chat_name = chat.title or "Private Chat"
            
            # Calculate current position
            current_pos = int(self.player.get_current_position(chat_id))
            
            # Format message
            formatted = self.formatter.format_now_playing(
                current_track.to_dict(),
                current_pos,
                chat_name,
                self.localization,
                chat_id
            )
            
            # Build keyboard
            keyboard = self.keyboards.build_playback_controls(
                chat_id,
                self.player.is_playing(chat_id),
                self.localization
            )
            
            # Send or edit message
            message_id = self.player.current_messages.get(chat_id)
            if message_id:
                try:
                    await self.bot.edit_message_text(
                        chat_id,
                        message_id,
                        formatted,
                        reply_markup=keyboard
                    )
                except Exception:
                    # Message might be deleted, send new one
                    message = await self.bot.send_message(
                        chat_id,
                        formatted,
                        reply_markup=keyboard
                    )
                    self.player.current_messages[chat_id] = message.id
            else:
                # Send new message
                message = await self.bot.send_message(
                    chat_id,
                    formatted,
                    reply_markup=keyboard
                )
                self.player.current_messages[chat_id] = message.id
                
        except Exception as e:
            self.logger.error(f"Failed to update now playing message for chat {chat_id}: {e}")
    
    async def start(self):
        """Start the bot."""
        if self.is_running:
            self.logger.warning("Bot is already running")
            return
        
        try:
            self.logger.info("Starting bot...")
            
            if not self.bot or not self.assistant or not self.pytgcalls:
                await self.initialize()
            
            self.is_running = True
            
            # Start state restoration
            await self._restore_playback_states()
            
            self.logger.info("Bot started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the bot."""
        if not self.is_running:
            return
        
        try:
            self.logger.info("Stopping bot...")
            
            self.is_running = False
            
            # Stop all components
            if self.pytgcalls:
                await self.pytgcalls.stop()
            
            if self.bot:
                await self.bot.stop()
            
            if self.assistant:
                await self.assistant.stop()
            
            # Clean up state managers
            if self.state_manager:
                for chat_id in list(self.state_manager.save_tasks.keys()):
                    await self.state_manager.stop_auto_save(chat_id)
            
            self.logger.info("Bot stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
    
    async def _restore_playback_states(self):
        """Restore saved playback states on startup."""
        try:
            if not self.state_manager:
                return
            
            self.logger.info("Restoring playback states...")
            
            restored_states = await self.state_manager.restore_playback_states()
            
            for chat_id, state_data in restored_states.items():
                try:
                    track_info = state_data.get("track", {})
                    position = state_data.get("restored_position", 0)
                    
                    self.logger.info(f"Restoring playback for chat {chat_id}: {track_info.get('title', 'Unknown')}")
                    
                    # Start playback
                    if self.player:
                        success = await self.player.play_audio(
                            chat_id,
                            track_info.get("file_path", ""),
                            resume_from=position
                        )
                        
                        if success:
                            # Start progress updater
                            await self._update_now_playing_message(chat_id)
                            
                            # Send restoration message
                            await self.bot.send_message(
                                chat_id,
                                self.localization.get_text(chat_id, "status_messages.bot_restarted")
                            )
                        else:
                            self.logger.error(f"Failed to restore playback for chat {chat_id}")
                
                except Exception as e:
                    self.logger.error(f"Failed to restore state for chat {chat_id}: {e}")
            
            self.logger.info("Playback state restoration completed")
            
        except Exception as e:
            self.logger.error(f"Error during state restoration: {e}")
    
    async def health_check(self) -> dict:
        """Get bot health status."""
        try:
            health = {
                "status": "healthy" if self.is_running else "stopped",
                "clients": {
                    "bot": self.bot.is_connected if self.bot else False,
                    "assistant": self.assistant.is_connected if self.assistant else False,
                    "pytgcalls": self.pytgcalls.is_running if self.pytgcalls else False,
                },
                "components": {
                    "player": self.player is not None,
                    "queue_manager": self.queue_manager is not None,
                    "localization": self.localization is not None,
                    "youtube": self.youtube is not None,
                    "state_manager": self.state_manager is not None,
                }
            }
            
            # Add active chats info if components are available
            if self.state_manager:
                health["active_chats"] = self.state_manager.get_state_summary()
            
            return health
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
