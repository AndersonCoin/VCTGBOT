"""
Queue management module for per-chat music queues.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """Represents a music track."""
    file_path: str
    title: str
    artist: str
    duration: int  # in seconds
    thumbnail: Optional[str] = None
    source_url: Optional[str] = None
    added_by: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert track to dictionary."""
        return {
            'file_path': self.file_path,
            'title': self.title,
            'artist': self.artist,
            'duration': self.duration,
            'thumbnail': self.thumbnail,
            'source_url': self.source_url,
            'added_by': self.added_by,
            'metadata': self.metadata
        }


class QueueManager:
    """Per-chat queue management."""
    
    def __init__(self):
        """Initialize queue manager."""
        self.queues: Dict[int, List[Track]] = defaultdict(list)
        self.current_index: Dict[int, int] = defaultdict(lambda: -1)
        self.loop_tracks: Dict[int, bool] = defaultdict(bool)
        self.shuffle_mode: Dict[int, bool] = defaultdict(False)
    
    def add_track(self, chat_id: int, track: Track) -> int:
        """Add a track to the queue."""
        self.queues[chat_id].append(track)
        index = len(self.queues[chat_id]) - 1
        logger.info(f"Added track to queue {chat_id}: {track.title}")
        return index
    
    def add_tracks(self, chat_id: int, tracks: List[Track]) -> List[int]:
        """Add multiple tracks to the queue."""
        indexes = []
        for track in tracks:
            index = self.add_track(chat_id, track)
            indexes.append(index)
        return indexes
    
    def get_current_track(self, chat_id: int) -> Optional[Track]:
        """Get current playing track."""
        if not self.queues[chat_id]:
            return None
        
        current_idx = self.current_index[chat_id]
        if current_idx == -1 or current_idx >= len(self.queues[chat_id]):
            return None
        
        return self.queues[chat_id][current_idx]
    
    def get_next_track(self, chat_id: int) -> Optional[Track]:
        """Get next track in queue."""
        if not self.queues[chat_id]:
            return None
        
        current_idx = self.current_index[chat_id]
        next_idx = current_idx + 1
        
        if next_idx >= len(self.queues[chat_id]):
            # End of queue
            if self.loop_tracks[chat_id]:
                # Loop from beginning if loop mode is on
                next_idx = 0
            else:
                return None
        
        self.current_index[chat_id] = next_idx
        return self.queues[chat_id][next_idx]
    
    def get_previous_track(self, chat_id: int) -> Optional[Track]:
        """Get previous track in queue."""
        if not self.queues[chat_id]:
            return None
        
        current_idx = self.current_index[chat_id]
        prev_idx = current_idx - 1
        
        if prev_idx < 0:
            # Beginning of queue
            if self.loop_tracks[chat_id]:
                # Loop to end if loop mode is on
                prev_idx = len(self.queues[chat_id]) - 1
            else:
                return None
        
        self.current_index[chat_id] = prev_idx
        return self.queues[chat_id][prev_idx]
    
    def skip_to_track(self, chat_id: int, index: int) -> Optional[Track]:
        """Skip to a specific track in queue."""
        if not self.queues[chat_id] or index < 0 or index >= len(self.queues[chat_id]):
            return None
        
        self.current_index[chat_id] = index
        return self.queues[chat_id][index]
    
    def remove_track(self, chat_id: int, index: int) -> bool:
        """Remove a track from queue."""
        if not self.queues[chat_id] or index < 0 or index >= len(self.queues[chat_id]):
            return False
        
        removed = self.queues[chat_id].pop(index)
        
        # Adjust current index if necessary
        current_idx = self.current_index[chat_id]
        if index < current_idx:
            self.current_index[chat_id] = current_idx - 1
        elif index == current_idx:
            # Removed current track
            if index >= len(self.queues[chat_id]):
                # Was last track, go to previous
                self.current_index[chat_id] = max(0, index - 1)
            # else stay at current index (which now points to next track)
        
        logger.info(f"Removed track from queue {chat_id}: {removed.title}")
        return True
    
    def clear_queue(self, chat_id: int):
        """Clear all tracks from queue."""
        self.queues[chat_id].clear()
        self.current_index[chat_id] = -1
        logger.info(f"Cleared queue for chat {chat_id}")
    
    def shuffle_queue(self, chat_id: int) -> bool:
        """Shuffle queue."""
        if len(self.queues[chat_id]) <= 1:
            return False
        
        current_track = self.get_current_track(chat_id)
        
        # Shuffle everything except current track
        remaining = self.queues[chat_id][self.current_index[chat_id] + 1:]
        import random
        random.shuffle(remaining)
        
        # Rebuild queue
        self.queues[chat_id] = self.queues[chat_id][:self.current_index[chat_id] + 1] + remaining
        
        self.shuffle_mode[chat_id] = True
        logger.info(f"Shuffled queue for chat {chat_id}")
        return True
    
    def set_loop_mode(self, chat_id: int, enabled: bool):
        """Set loop mode for queue."""
        self.loop_tracks[chat_id] = enabled
        logger.info(f"Set loop mode to {enabled} for chat {chat_id}")
    
    def is_looping(self, chat_id: int) -> bool:
        """Check if loop mode is enabled."""
        return self.loop_tracks[chat_id]
    
    def is_shuffling(self, chat_id: int) -> bool:
        """Check if shuffle mode is enabled."""
        return self.shuffle_mode[chat_id]
    
    def get_queue_info(self, chat_id: int) -> Dict[str, Any]:
        """Get queue information."""
        queue = self.queues[chat_id]
        current_idx = self.current_index[chat_id]
        
        # Calculate total duration
        total_duration = sum(track.duration for track in queue)
        
        return {
            'total_tracks': len(queue),
            'current_index': current_idx,
            'current_track': self.get_current_track(chat_id) if current_idx != -1 else None,
            'total_duration': total_duration,
            'is_looping': self.loop_tracks[chat_id],
            'is_shuffling': self.shuffle_mode[chat_id],
            'queue': queue
        }
    
    def get_page(self, chat_id: int, page: int = 0, page_size: int = 10) -> Dict[str, Any]:
        """Get paginated queue."""
        queue = self.queues[chat_id]
        total_pages = (len(queue) + page_size - 1) // page_size
        
        start_idx = page * page_size
        end_idx = start_idx + page_size
        
        page_tracks = queue[start_idx:end_idx]
        
        return {
            'tracks': page_tracks,
            'page': page,
            'total_pages': total_pages,
            'total_tracks': len(queue),
            'has_previous': page > 0,
            'has_next': page < total_pages - 1
        }
    
    def start_playback(self, chat_id: int) -> Optional[Track]:
        """Start playback from beginning of queue."""
        if not self.queues[chat_id]:
            return None
        
        self.current_index[chat_id] = 0
        return self.queues[chat_id][0]
    
    def auto_next(self, chat_id: int) -> Optional[Track]:
        """Automatically move to next track."""
        return self.get_next_track(chat_id)
    
    def get_queue_length(self, chat_id: int) -> int:
        """Get queue length."""
        return len(self.queues[chat_id])
    
    def is_empty(self, chat_id: int) -> bool:
        """Check if queue is empty."""
        return len(self.queues[chat_id]) == 0
