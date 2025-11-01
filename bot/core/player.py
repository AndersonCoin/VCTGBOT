"""
Music player module for managing voice chat playback.
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from pytgcalls import PyTgCalls
from pytgcalls.exceptions import (
    NoActiveGroupCall,
    GroupCallNotFound,
    NotConnectedError
)
from pytgcalls.types import (
    Update,
    GroupCallParticipant,
    GroupCall,
    AudioStream,
    VideoStream,
    StreamAudioEnded
)

logger = logging.getLogger(__name__)


class Player:
    """Music player with PyTgCalls integration."""
    
    def __init__(self, pytgcalls: PyTgCalls):
        """Initialize the player."""
        self.pytgcalls = pytgcalls
        self.progress_updaters: Dict[int, asyncio.Task] = {}
        self.playback_state: Dict[int, Dict[str, Any]] = {}
        self.current_messages: Dict[int, int] = {}  # chat_id -> message_id
    
    async def join_voice_chat(self, chat_id: int) -> bool:
        """Join a voice chat."""
        try:
            await self.pytgcalls.join_group_call(chat_id, None)
            logger.info(f"Joined voice chat: {chat_id}")
            return True
        except (NoActiveGroupCall, GroupCallNotFound):
            logger.warning(f"No active voice chat in {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to join voice chat {chat_id}: {e}")
            return False
    
    async def leave_voice_chat(self, chat_id: int) -> bool:
        """Leave a voice chat."""
        try:
            await self.pytgcalls.leave_group_call(chat_id)
            logger.info(f"Left voice chat: {chat_id}")
            
            # Clean up updater
            if chat_id in self.progress_updaters:
                self.progress_updaters[chat_id].cancel()
                del self.progress_updaters[chat_id]
            
            # Clean up message reference
            if chat_id in self.current_messages:
                del self.current_messages[chat_id]
            
            return True
        except Exception as e:
            logger.error(f"Failed to leave voice chat {chat_id}: {e}")
            return False
    
    async def play_audio(self, chat_id: int, file_path: str, resume_from: int = 0) -> bool:
        """Play audio file in voice chat."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"Audio file not found: {file_path}")
                return False
            
            # Stop current playback if any
            await self.stop_playback(chat_id)
            
            # Start playback
            await self.pytgcalls.join_group_call(
                chat_id,
                AudioStream(file_path=file_path, start_point=resume_from)
            )
            
            # Save playback state
            self.playback_state[chat_id] = {
                'file_path': str(file_path),
                'start_time': asyncio.get_event_loop().time(),
                'resume_from': resume_from,
                'is_playing': True
            }
            
            logger.info(f"Started playback in {chat_id}: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to play audio in {chat_id}: {e}")
            return False
    
    async def pause_playback(self, chat_id: int) -> bool:
        """Pause current playback."""
        try:
            await self.pytgcalls.pause_group_call(chat_id)
            
            if chat_id in self.playback_state:
                self.playback_state[chat_id]['is_playing'] = False
                self.playback_state[chat_id]['paused_at'] = asyncio.get_event_loop().time()
            
            logger.info(f"Paused playback in {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause playback in {chat_id}: {e}")
            return False
    
    async def resume_playback(self, chat_id: int) -> bool:
        """Resume paused playback."""
        try:
            await self.pytgcalls.resume_group_call(chat_id)
            
            if chat_id in self.playback_state:
                self.playback_state[chat_id]['is_playing'] = True
                self.playback_state[chat_id]['resume_at'] = asyncio.get_event_loop().time()
            
            logger.info(f"Resumed playback in {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume playback in {chat_id}: {e}")
            return False
    
    async def stop_playback(self, chat_id: int) -> bool:
        """Stop current playback."""
        try:
            await self.pytgcalls.leave_group_call(chat_id)
            
            # Clean up state
            if chat_id in self.playback_state:
                del self.playback_state[chat_id]
            
            if chat_id in self.progress_updaters:
                self.progress_updaters[chat_id].cancel()
                del self.progress_updaters[chat_id]
            
            logger.info(f"Stopped playback in {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop playback in {chat_id}: {e}")
            return False
    
    async def skip_track(self, chat_id: int) -> bool:
        """Skip current track."""
        try:
            await self.stop_playback(chat_id)
            logger.info(f"Skipped track in {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to skip track in {chat_id}: {e}")
            return False
    
    def get_current_position(self, chat_id: int) -> float:
        """Get current playback position in seconds."""
        if chat_id not in self.playback_state:
            return 0.0
        
        state = self.playback_state[chat_id]
        if not state.get('is_playing', False):
            return state.get('resume_from', 0.0)
        
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - state['start_time']
        return state['resume_from'] + elapsed
    
    def get_playback_state(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get current playback state."""
        return self.playback_state.get(chat_id)
    
    def is_playing(self, chat_id: int) -> bool:
        """Check if music is currently playing."""
        return chat_id in self.playback_state and self.playback_state[chat_id].get('is_playing', False)
    
    async def start_progress_updater(self, chat_id: int, message_id: int, update_func):
        """Start periodic progress updates for now playing message."""
        if chat_id in self.progress_updaters:
            self.progress_updaters[chat_id].cancel()
        
        # Store message reference
        self.current_messages[chat_id] = message_id
        
        async def updater():
            while chat_id in self.progress_updaters:
                try:
                    if chat_id in self.current_messages:
                        await update_func(chat_id, self.current_messages[chat_id])
                except Exception as e:
                    logger.error(f"Progress updater error for {chat_id}: {e}")
                
                await asyncio.sleep(15)  # Update every 15 seconds
        
        self.progress_updaters[chat_id] = asyncio.create_task(updater())
    
    async def stop_progress_updater(self, chat_id: int):
        """Stop progress updater for a chat."""
        if chat_id in self.progress_updaters:
            self.progress_updaters[chat_id].cancel()
            del self.progress_updaters[chat_id]
        
        if chat_id in self.current_messages:
            del self.current_messages[chat_id]
    
    def register_handlers(self, on_stream_end=None):
        """Register PyTgCalls event handlers."""
        
        @self.pytgcalls.on_update()
        async def handle_update(update: Update):
            """Handle PyTgCalls updates."""
            try:
                if isinstance(update, StreamAudioEnded):
                    logger.info(f"Stream ended for chat {update.chat_id}")
                    if on_stream_end:
                        await on_stream_end(update.chat_id)
            except Exception as e:
                logger.error(f"Error handling update: {e}")
    
    def handle_stream_end(self, chat_id: int):
        """Handle stream end event - to be implemented by queue manager."""
        pass
