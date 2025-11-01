"""
Text formatting helpers for music bot.
"""
import re
from typing import Optional, Dict, Any
from datetime import timedelta

from bot.helpers.localization import Localization


class Formatter:
    """Text formatting utilities."""
    
    @staticmethod
    def format_duration(seconds: int, localization: Localization, chat_id: int) -> str:
        """Format duration in human readable format."""
        return localization.format_duration(seconds, chat_id)
    
    @staticmethod
    def format_progress_bar(
        current: int, 
        total: int, 
        localization: Localization, 
        chat_id: int
    ) -> str:
        """Format progress bar."""
        return localization.format_progress_bar(current, total, chat_id)
    
    @staticmethod
    def format_now_playing(
        track: Dict[str, Any],
        current_pos: int,
        chat_name: str,
        localization: Localization,
        chat_id: int
    ) -> str:
        """Format now playing message."""
        duration = Formatter.format_duration(track.get('duration', 0), localization, chat_id)
        position = Formatter.format_duration(current_pos, localization, chat_id)
        progress_bar = Formatter.format_progress_bar(current_pos, track.get('duration', 0), localization, chat_id)
        
        return localization.get_text(
            chat_id,
            "now_playing",
            title=Formatter.sanitize_text(track.get('title', 'Unknown')),
            artist=Formatter.sanitize_text(track.get('artist', 'Unknown')),
            duration=duration,
            chat_name=Formatter.sanitize_text(chat_name),
            progress_bar=progress_bar,
            position=position
        )
    
    @staticmethod
    def format_queue_header(
        queue_info: Dict[str, Any],
        localization: Localization,
        chat_id: int
    ) -> str:
        """Format queue header."""
        total_tracks = queue_info.get('total_tracks', 0)
        current_track = queue_info.get('current_track')
        current_title = Formatter.sanitize_text(current_track.get('title', 'None')) if current_track else 'None'
        
        total_duration = queue_info.get('total_duration', 0)
        formatted_duration = Formatter.format_duration(total_duration, localization, chat_id)
        
        return localization.get_text(
            chat_id,
            "queue_header",
            current=current_title,
            total=total_tracks,
            total_duration=formatted_duration
        )
    
    @staticmethod
    def format_added_to_queue(
        track: Dict[str, Any],
        localization: Localization,
        chat_id: int
    ) -> str:
        """Format added to queue message."""
        duration = Formatter.format_duration(track.get('duration', 0), localization, chat_id)
        
        return localization.get_text(
            chat_id,
            "added_to_queue",
            title=Formatter.sanitize_text(track.get('title', 'Unknown')),
            artist=Formatter.sanitize_text(track.get('artist', 'Unknown')),
            duration=duration
        )
    
    @staticmethod
    def format_downloading(track_title: str, localization: Localization, chat_id: int) -> str:
        """Format downloading message."""
        return localization.get_text(
            chat_id,
            "downloading",
            title=Formatter.sanitize_text(track_title)
        )
    
    @staticmethod
    def format_error(error_key: str, **kwargs) -> str:
        """Format error message."""
        # This would need access to localization, so it should be called from context
        # Returning a basic error format as fallback
        return f"❌ Error: {error_key}"
    
    @staticmethod
    def format_status(status_key: str, **kwargs) -> str:
        """Format status message."""
        # This would need access to localization, so it should be called from context
        # Returning a basic status format as fallback
        return f"✅ {status_key}"
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize text for safe display."""
        if not text:
            return "Unknown"
        
        # Remove or replace problematic characters
        text = re.sub(r'[<>"\']', '', text)  # Remove HTML chars
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length-3] + "..."
        
        return text
    
    @staticmethod
    def format_time_delta(seconds: int) -> str:
        """Format time delta in human readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    @staticmethod
    def format_search_results(results: list, localization: Localization, chat_id: int) -> str:
        """Format search results list."""
        if not results:
            return "No results found."
        
        formatted = []
        for i, result in enumerate(results[:10], 1):  # Limit to 10 results
            title = Formatter.sanitize_text(result.get('title', 'Unknown'), 50)
            duration = Formatter.format_duration(result.get('duration', 0), localization, chat_id)
            uploader = Formatter.sanitize_text(result.get('uploader', 'Unknown'), 30)
            
            formatted.append(f"{i}. **{title}**\n   👤 {uploader} • ⏱️ {duration}")
        
        return "\n\n".join(formatted)
    
    @staticmethod
    def format_track_info(track: Dict[str, Any], localization: Localization, chat_id: int) -> str:
        """Format detailed track information."""
        title = Formatter.sanitize_text(track.get('title', 'Unknown'))
        artist = Formatter.sanitize_text(track.get('artist', 'Unknown'))
        duration = Formatter.format_duration(track.get('duration', 0), localization, chat_id)
        view_count = track.get('view_count', 0)
        
        info = f"🎵 **{title}**\n"
        info += f"👤 **Artist:** {artist}\n"
        info += f"⏱️ **Duration:** {duration}\n"
        info += f"👁️ **Views:** {view_count:,}\n"
        
        # Add description if available
        description = track.get('description', '')
        if description:
            desc = Formatter.sanitize_text(description[:200])
            if len(description) > 200:
                desc += "..."
            info += f"\n📝 **Description:**\n{desc}"
        
        return info
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 50) -> str:
        """Truncate text with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape markdown special characters."""
        special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
