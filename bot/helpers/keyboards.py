"""
Inline keyboard builders for bot interface.
"""
from typing import List, Dict, Any, Optional
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class KeyboardBuilder:
    """Builder for inline keyboards."""
    
    @staticmethod
    def build_playback_controls(chat_id: int, is_playing: bool, localization) -> InlineKeyboardMarkup:
        """Build playback control keyboard."""
        buttons = []
        
        # Pause/Resume button
        if is_playing:
            pause_text = localization.get_text_by_lang(
                "en", "playback_controls.pause"
            )  # Use English for button text consistency
            callback_data = f"player_pause:{chat_id}"
        else:
            pause_text = localization.get_text_by_lang(
                "en", "playback_controls.resume"
            )
            callback_data = f"player_play:{chat_id}"
        
        buttons.append([InlineKeyboardButton(pause_text, callback_data=callback_data)])
        
        # Other control buttons
        skip_text = localization.get_text_by_lang("en", "playback_controls.skip")
        stop_text = localization.get_text_by_lang("en", "playback_controls.stop")
        queue_text = localization.get_text_by_lang("en", "playback_controls.queue")
        settings_text = localization.get_text_by_lang("en", "playback_controls.settings")
        
        buttons.append([
            InlineKeyboardButton(skip_text, callback_data=f"player_skip:{chat_id}"),
            InlineKeyboardButton(stop_text, callback_data=f"player_stop:{chat_id}"),
        ])
        
        buttons.append([
            InlineKeyboardButton(queue_text, callback_data=f"queue_open:{chat_id}:0"),
            InlineKeyboardButton(settings_text, callback_data=f"player_settings:{chat_id}"),
        ])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_queue_navigation(
        chat_id: int, 
        page: int, 
        total_pages: int, 
        localization
    ) -> InlineKeyboardMarkup:
        """Build queue navigation keyboard."""
        buttons = []
        
        # Navigation buttons
        nav_buttons = []
        
        if page > 0:
            prev_text = localization.get_text_by_lang("en", "queue_controls.previous")
            nav_buttons.append(
                InlineKeyboardButton(prev_text, callback_data=f"queue_nav:{chat_id}:{page-1}")
            )
        
        if page < total_pages - 1:
            next_text = localization.get_text_by_lang("en", "queue_controls.next")
            nav_buttons.append(
                InlineKeyboardButton(next_text, callback_data=f"queue_nav:{chat_id}:{page+1}")
            )
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Refresh and back buttons
        buttons.append([
            InlineKeyboardButton(
                localization.get_text_by_lang("en", "queue_controls.refresh"),
                callback_data=f"queue_open:{chat_id}:{page}"
            ),
            InlineKeyboardButton(
                localization.get_text_by_lang("en", "queue_controls.back_to_player"),
                callback_data=f"player_back:{chat_id}"
            ),
        ])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_settings_menu(chat_id: int, localization) -> InlineKeyboardMarkup:
        """Build settings menu keyboard."""
        buttons = []
        
        # Volume controls
        volume_up_text = localization.get_text_by_lang("en", "settings_controls.volume_up")
        volume_down_text = localization.get_text_by_lang("en", "settings_controls.volume_down")
        
        buttons.append([
            InlineKeyboardButton(volume_up_text, callback_data=f"volume_up:{chat_id}"),
            InlineKeyboardButton(volume_down_text, callback_data=f"volume_down:{chat_id}"),
        ])
        
        # Loop and shuffle
        loop_text = localization.get_text_by_lang("en", "settings_controls.loop_track")
        shuffle_text = localization.get_text_by_lang("en", "settings_controls.shuffle")
        
        buttons.append([
            InlineKeyboardButton(loop_text, callback_data=f"loop_toggle:{chat_id}"),
            InlineKeyboardButton(shuffle_text, callback_data=f"shuffle_queue:{chat_id}"),
        ])
        
        # Back button
        buttons.append([
            InlineKeyboardButton(
                localization.get_text_by_lang("en", "settings_controls.back_to_player"),
                callback_data=f"player_back:{chat_id}"
            )
        ])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_language_selection(current_lang: str, localization) -> InlineKeyboardMarkup:
        """Build language selection keyboard."""
        buttons = []
        
        langs = localization.get_available_languages()
        
        for lang_code, lang_name in langs.items():
            # Mark current language
            if lang_code == current_lang:
                text = f"✅ {lang_name}"
            else:
                text = lang_name
            
            buttons.append([InlineKeyboardButton(text, callback_data=f"lang_set:{lang_code}")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_track_queue_items(
        chat_id: int,
        tracks: List[Dict[str, Any]],
        current_index: int,
        page: int,
        localization
    ) -> List[List[InlineKeyboardButton]]:
        """Build queue track list buttons."""
        buttons = []
        
        for i, track in enumerate(tracks):
            global_index = page * 10 + i  # Assuming 10 tracks per page
            
            if global_index == current_index:
                # Current playing track
                text = f"▶️ {track['title'][:30]}..."
            else:
                text = f"{global_index + 1}. {track['title'][:30]}..."
            
            # Add callback to skip to this track
            callback_data = f"queue_skip:{chat_id}:{global_index}"
            buttons.append([InlineKeyboardButton(text, callback_data=callback_data)])
        
        return buttons
    
    @staticmethod
    def build_confirmation_keyboard(chat_id: int, action: str, localization) -> InlineKeyboardMarkup:
        """Build confirmation keyboard for admin actions."""
        buttons = []
        
        confirm_text = "✅ Confirm"
        cancel_text = "❌ Cancel"
        
        buttons.append([
            InlineKeyboardButton(confirm_text, callback_data=f"confirm_{action}:{chat_id}"),
            InlineKeyboardButton(cancel_text, callback_data=f"cancel_{action}:{chat_id}"),
        ])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def build_simple_back_button(chat_id: int, localization) -> InlineKeyboardMarkup:
        """Build simple back button."""
        buttons = [
            [InlineKeyboardButton(
                localization.get_text_by_lang("en", "queue_controls.back_to_player"),
                callback_data=f"player_back:{chat_id}"
            )]
        ]
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def parse_callback_data(callback_data: str) -> Dict[str, Any]:
        """Parse callback data to extract action and parameters."""
        parts = callback_data.split(":")
        
        if len(parts) < 1:
            return {"action": "unknown"}
        
        action = parts[0]
        params = parts[1:] if len(parts) > 1 else []
        
        result = {"action": action, "params": params}
        
        # Parse common parameters
        if len(params) >= 1:
            try:
                result["chat_id"] = int(params[0])
            except ValueError:
                result["chat_id"] = params[0]
        
        if len(params) >= 2:
            try:
                result["page"] = int(params[1])
            except ValueError:
                result["page"] = params[1]
        
        if len(params) >= 3:
            try:
                result["index"] = int(params[2])
            except ValueError:
                result["index"] = params[2]
        
        return result
    
    @staticmethod
    def validate_callback_data(callback_data: str) -> bool:
        """Validate callback data format."""
        if len(callback_data) > 64:
            return False
        
        # Basic validation - alphanumeric, underscore, colon, hyphen only
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-')
        return all(c in allowed_chars for c in callback_data)
