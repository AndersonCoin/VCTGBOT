"""
State management for persistent playback state across bot restarts.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent playback state."""
    
    def __init__(self, storage_backend, state_dir: Path = Path("state")):
        """Initialize state manager."""
        self.storage = storage_backend
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.save_interval = 15  # Save every 15 seconds
        self.save_tasks: Dict[int, asyncio.Task] = {}
        self.pending_saves: Dict[int, Dict[str, Any]] = {}
    
    async def save_playback_state(
        self, 
        chat_id: int, 
        track_info: Dict[str, Any],
        position: float,
        is_playing: bool = True
    ) -> bool:
        """Save current playback state."""
        try:
            state_data = {
                "chat_id": chat_id,
                "track": track_info,
                "position": position,
                "is_playing": is_playing,
                "timestamp": datetime.now().isoformat(),
                "last_updated": asyncio.get_event_loop().time()
            }
            
            self.pending_saves[chat_id] = state_data
            
            # Schedule immediate save for important state changes
            if not is_playing:  # Paused or stopped
                await self._perform_save(chat_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save state for chat {chat_id}: {e}")
            return False
    
    async def get_playback_state(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get saved playback state for chat."""
        try:
            state_key = f"playback_state:{chat_id}"
            state_data = await self.storage.get(state_key)
            
            if state_data:
                # Parse the data if it's a string
                if isinstance(state_data, str):
                    state_data = json.loads(state_data)
                
                logger.info(f"Loaded playback state for chat {chat_id}")
                return state_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get state for chat {chat_id}: {e}")
            return None
    
    async def delete_playback_state(self, chat_id: int) -> bool:
        """Delete playback state for chat."""
        try:
            state_key = f"playback_state:{chat_id}"
            await self.storage.delete(state_key)
            
            # Cancel any pending save tasks
            if chat_id in self.save_tasks:
                self.save_tasks[chat_id].cancel()
                del self.save_tasks[chat_id]
            
            if chat_id in self.pending_saves:
                del self.pending_saves[chat_id]
            
            logger.info(f"Deleted playback state for chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete state for chat {chat_id}: {e}")
            return False
    
    async def start_auto_save(self, chat_id: int) -> bool:
        """Start automatic periodic saving for chat."""
        try:
            # Cancel existing task if any
            if chat_id in self.save_tasks:
                self.save_tasks[chat_id].cancel()
            
            # Create new auto-save task
            async def auto_save():
                while chat_id in self.save_tasks:
                    try:
                        await asyncio.sleep(self.save_interval)
                        if chat_id in self.pending_saves:
                            await self._perform_save(chat_id)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Auto-save error for chat {chat_id}: {e}")
            
            self.save_tasks[chat_id] = asyncio.create_task(auto_save())
            logger.info(f"Started auto-save for chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start auto-save for chat {chat_id}: {e}")
            return False
    
    async def stop_auto_save(self, chat_id: int) -> bool:
        """Stop automatic saving for chat."""
        try:
            if chat_id in self.save_tasks:
                self.save_tasks[chat_id].cancel()
                del self.save_tasks[chat_id]
            
            # Perform final save
            if chat_id in self.pending_saves:
                await self._perform_save(chat_id)
            
            logger.info(f"Stopped auto-save for chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop auto-save for chat {chat_id}: {e}")
            return False
    
    async def _perform_save(self, chat_id: int) -> bool:
        """Perform the actual save operation."""
        try:
            if chat_id not in self.pending_saves:
                return False
            
            state_data = self.pending_saves[chat_id]
            state_key = f"playback_state:{chat_id}"
            
            # Store as JSON string
            await self.storage.set(state_key, json.dumps(state_data))
            
            logger.debug(f"Saved state for chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to perform save for chat {chat_id}: {e}")
            return False
    
    async def get_all_saved_states(self) -> List[Dict[str, Any]]:
        """Get all saved playback states."""
        try:
            states = []
            state_pattern = "playback_state:*"
            
            saved_states = await self.storage.get_pattern(state_pattern)
            
            for key, value in saved_states.items():
                try:
                    if isinstance(value, str):
                        state_data = json.loads(value)
                    else:
                        state_data = value
                    
                    states.append(state_data)
                except Exception as e:
                    logger.error(f"Failed to parse state data for key {key}: {e}")
            
            return states
            
        except Exception as e:
            logger.error(f"Failed to get all saved states: {e}")
            return []
    
    async def cleanup_old_states(self, max_age_hours: int = 24) -> int:
        """Clean up old playback states."""
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            cleaned_count = 0
            
            saved_states = await self.storage.get_pattern("playback_state:*")
            
            for key, value in saved_states.items():
                try:
                    if isinstance(value, str):
                        state_data = json.loads(value)
                    else:
                        state_data = value
                    
                    # Check if state is old enough
                    timestamp = state_data.get("timestamp")
                    if timestamp:
                        state_time = datetime.fromisoformat(timestamp).timestamp()
                        if state_time < cutoff_time:
                            await self.storage.delete(key)
                            cleaned_count += 1
                
                except Exception as e:
                    logger.error(f"Failed to process state {key} for cleanup: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} old states")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old states: {e}")
            return 0
    
    async def restore_playback_states(self) -> Dict[int, Dict[str, Any]]:
        """Restore all saved playback states on startup."""
        try:
            restored_states = {}
            saved_states = await self.storage.get_pattern("playback_state:*")
            
            for key, value in saved_states.items():
                try:
                    # Extract chat_id from key
                    if key.startswith("playback_state:"):
                        chat_id = int(key.split(":")[1])
                    else:
                        continue
                    
                    if isinstance(value, str):
                        state_data = json.loads(value)
                    else:
                        state_data = value
                    
                    # Calculate current position
                    last_updated = state_data.get("last_updated", 0)
                    position = state_data.get("position", 0)
                    
                    # If was playing, estimate current position
                    if state_data.get("is_playing", False) and last_updated > 0:
                        current_time = asyncio.get_event_loop().time()
                        time_diff = current_time - last_updated
                        
                        # Assume average track duration for estimation
                        track_duration = state_data.get("track", {}).get("duration", 300)
                        if time_diff < track_duration:
                            position += time_diff
                    
                    state_data["restored_position"] = min(position, state_data.get("track", {}).get("duration", 0))
                    restored_states[chat_id] = state_data
                    
                except Exception as e:
                    logger.error(f"Failed to restore state from key {key}: {e}")
            
            logger.info(f"Restored {len(restored_states)} playback states")
            return restored_states
            
        except Exception as e:
            logger.error(f"Failed to restore playback states: {e}")
            return {}
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state."""
        return {
            "active_chats": len(self.save_tasks),
            "pending_saves": len(self.pending_saves),
            "save_interval": self.save_interval
        }
