"""
General callback query handlers for inline buttons.
"""
import logging
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

from bot.client import BotClient
from bot.helpers.keyboards import KeyboardBuilder

logger = logging.getLogger(__name__)


async def general_callback(client: BotClient, callback: CallbackQuery):
    """Handle general callbacks not handled by specific plugins."""
    try:
        data = KeyboardBuilder.parse_callback_data(callback.data)
        
        # Validate callback data
        if not KeyboardBuilder.validate_callback_data(callback.data):
            await callback.answer("❌ Invalid callback data")
            return
        
        action = data["action"]
        
        if action == "player_settings":
            # Show settings menu
            await _show_settings_menu(client, callback)
            
        elif action == "queue_open":
            # Open queue view
            page = data.get("page", 0)
            chat_id = data.get("chat_id", 0)
            await _open_queue_view(client, chat_id, page, callback)
            
        elif action == "confirm_stop":
            # Confirm stop action
            chat_id = data.get("chat_id", 0)
            await _confirm_stop_action(client, chat_id, callback)
            
        elif action == "cancel_action":
            # Cancel current action
            await callback.answer("Action cancelled")
            await callback.message.edit_reply_markup(None)
            
        else:
            # Unknown action
            await callback.answer("Unknown action")
        
    except Exception as e:
        logger.error(f"Error handling general callback: {e}")
        await callback.answer("❌ An error occurred")


async def _show_settings_menu(client: BotClient, callback: CallbackQuery):
    """Show settings menu."""
    try:
        from bot.helpers.keyboards import KeyboardBuilder
        data = KeyboardBuilder.parse_callback_data(callback.data)
        
        chat_id = data.get("chat_id", 0)
        
        # Build settings keyboard
        settings_keyboard = client.keyboards.build_settings_menu(chat_id, client.localization)
        
        # Format settings message
        settings_text = "⚙️ <b>Player Settings</b>\n\n"
        
        # Add current settings
        if client.queue_manager:
            is_looping = client.queue_manager.is_looping(chat_id)
            is_shuffling = client.queue_manager.is_shuffling(chat_id)
            
            settings_text += f"🔁 Loop Mode: {'Enabled' if is_looping else 'Disabled'}\n"
            settings_text += f"🔀 Shuffle Mode: {'Enabled' if is_shuffling else 'Disabled'}"
        
        await callback.message.edit_text(
            settings_text,
            reply_markup=settings_keyboard
        )
        
        await callback.answer("Settings opened")
        
    except Exception as e:
        logger.error(f"Error showing settings menu: {e}")
        await callback.answer("❌ Error opening settings")


async def _open_queue_view(client: BotClient, chat_id: int, page: int, callback: CallbackQuery):
    """Open queue view."""
    try:
        # Get queue information
        if not client.queue_manager:
            await callback.answer("Queue manager not available")
            return
        
        queue_info = client.queue_manager.get_queue_info(chat_id)
        total_tracks = queue_info["total_tracks"]
        
        if total_tracks == 0:
            empty_text = client.localization.get_text(chat_id, "queue_empty")
            await callback.message.edit_text(empty_text)
            return
        
        # Get page data
        page_data = client.queue_manager.get_page(chat_id, page)
        
        # Format queue header
        from bot.helpers.formatting import Formatter
        formatter = Formatter()
        queue_header = formatter.format_queue_header(
            queue_info,
            client.localization,
            chat_id
        )
        
        # Build queue list
        queue_text = await _format_queue_for_view(
            client,
            page_data["tracks"],
            queue_info["current_index"],
            page,
            chat_id
        )
        
        # Build keyboard
        queue_keyboard = client.keyboards.build_queue_navigation(
            chat_id,
            page,
            page_data["total_pages"],
            client.localization
        )
        
        # Update message
        full_text = f"{queue_header}\n\n{queue_text}"
        
        await callback.message.edit_text(
            full_text,
            reply_markup=queue_keyboard,
            disable_web_page_preview=True
        )
        
        await callback.answer(f"Queue (Page {page + 1})")
        
    except Exception as e:
        logger.error(f"Error opening queue view: {e}")
        await callback.answer("❌ Error loading queue")


async def _format_queue_for_view(
    client: BotClient, 
    tracks: list, 
    current_index: int, 
    page: int, 
    chat_id: int
) -> str:
    """Format queue for view."""
    try:
        if not tracks:
            return "No tracks in this page."
        
        queue_lines = []
        
        for i, track in enumerate(tracks):
            global_index = page * 10 + i
            
            # Format track info
            title = client.formatter.sanitize_text(track.title, 40)
            artist = client.formatter.sanitize_text(track.artist, 30)
            duration = client.formatter.format_duration(track.duration, client.localization, chat_id)
            
            # Add current track indicator
            if global_index == current_index:
                indicator = "▶️ "
            else:
                indicator = "  "
            
            line = f"{indicator}{global_index + 1}. **{title}**\n   👤 {artist} • ⏱️ {duration}"
            queue_lines.append(line)
        
        return "\n\n".join(queue_lines)
        
    except Exception as e:
        logger.error(f"Error formatting queue for view: {e}")
        return "Error formatting queue."


async def _confirm_stop_action(client: BotClient, chat_id: int, callback: CallbackQuery):
    """Confirm stop action."""
    try:
        # This could be expanded to show a confirmation dialog
        # For now, just proceed with stop
        
        # Stop playback and leave voice chat
        await client.player.stop_playback(chat_id)
        await client.player.leave_voice_chat(chat_id)
        
        # Stop auto-save
        await client.state_manager.stop_auto_save(chat_id)
        
        # Clear queue
        client.queue_manager.clear_queue(chat_id)
        
        # Update message
        await callback.message.edit_text(
            client.localization.get_text(chat_id, "status_messages.left_voice_chat"),
            reply_markup=None
        )
        
        await callback.answer("Playback stopped")
        
    except Exception as e:
        logger.error(f"Error confirming stop action: {e}")
        await callback.answer("❌ Error stopping playback")


async def handle_player_controls_callback(client: BotClient, callback: CallbackQuery):
    """Handle player controls callbacks."""
    try:
        data = KeyboardBuilder.parse_callback_data(callback.data)
        action = data["action"]
        chat_id = data.get("chat_id", 0)
        
        # Route to appropriate handler based on action
        if action in ["player_pause", "player_play"]:
            # These are handled in play.py
            pass
        elif action == "player_skip":
            # Handled in controls.py
            pass
        elif action == "player_stop":
            # Handled in controls.py
            pass
        elif action == "player_settings":
            await _show_settings_menu(client, callback)
        
    except Exception as e:
        logger.error(f"Error handling player controls callback: {e}")
        await callback.answer("❌ An error occurred")


async def handle_settings_callback(client: BotClient, callback: CallbackQuery):
    """Handle settings callbacks."""
    try:
        data = KeyboardBuilder.parse_callback_data(callback.data)
        action = data["action"]
        chat_id = data.get("chat_id", 0)
        
        if action == "volume_up":
            await callback.answer("Volume control not implemented yet")
            
        elif action == "volume_down":
            await callback.answer("Volume control not implemented yet")
            
        elif action == "loop_toggle":
            # Toggle loop mode
            if client.queue_manager:
                current_loop = client.queue_manager.is_looping(chat_id)
                client.queue_manager.set_loop_mode(chat_id, not current_loop)
                
                status = "enabled" if not current_loop else "disabled"
                await callback.answer(f"Loop mode {status}")
                
                # Update settings display
                await _show_settings_menu(client, callback)
            
        elif action == "shuffle":
            # Shuffle queue
            if client.queue_manager:
                success = client.queue_manager.shuffle_queue(chat_id)
                
                if success:
                    await callback.answer("Queue shuffled!")
                else:
                    await callback.answer("Cannot shuffle queue")
                
                # Update settings display
                await _show_settings_menu(client, callback)
            
        elif action == "player_back":
            # Return to player view
            await client._update_now_playing_message(chat_id)
            await callback.answer("Returned to player")
        
    except Exception as e:
        logger.error(f"Error handling settings callback: {e}")
        await callback.answer("❌ An error occurred")


async def handle_queue_callback(client: BotClient, callback: CallbackQuery):
    """Handle queue callbacks."""
    try:
        data = KeyboardBuilder.parse_callback_data(callback.data)
        action = data["action"]
        chat_id = data.get("chat_id", 0)
        
        if action == "queue_open":
            page = data.get("page", 0)
            await _open_queue_view(client, chat_id, page, callback)
            
        elif action == "queue_nav":
            page = data.get("page", 0)
            await _open_queue_view(client, chat_id, page, callback)
            
        elif action == "queue_skip":
            index = data.get("index", 0)
            await _skip_to_track(client, chat_id, index, callback)
            
        elif action == "queue_refresh":
            # Refresh current page
            await callback.answer("Refreshing queue...")
            # Re-open current queue view
            # (This would need the current page information)
            
        elif action == "player_back":
            # Return to player view
            await client._update_now_playing_message(chat_id)
            await callback.answer("Returned to player")
        
    except Exception as e:
        logger.error(f"Error handling queue callback: {e}")
        await callback.answer("❌ An error occurred")


async def _skip_to_track(client: BotClient, chat_id: int, index: int, callback: CallbackQuery):
    """Skip to specific track in queue."""
    try:
        # Skip to track
        track = client.queue_manager.skip_to_track(chat_id, index)
        
        if not track:
            await callback.answer("Track not found")
            return
        
        # Stop current playback
        await client.player.stop_playback(chat_id)
        
        # Start new track
        success = await client.player.play_audio(chat_id, track.file_path)
        
        if success:
            # Update now playing message
            await client._update_now_playing_message(chat_id)
            
            # Restart progress updater
            if chat_id in client.player.current_messages:
                await client.player.start_progress_updater(
                    chat_id,
                    client.player.current_messages[chat_id],
                    client._update_now_playing_message
                )
            
            await callback.answer(f"Playing: {track.title[:30]}...")
        else:
            await callback.answer("Failed to play track")
        
    except Exception as e:
        logger.error(f"Error skipping to track: {e}")
        await callback.answer("❌ Error skipping to track")


def register_handlers(app: Client, bot_client: BotClient):
    """Register all callback handlers."""
    
    @app.on_callback_query()
    async def handle_general_callback(client: Client, callback: CallbackQuery):
        # Route callbacks to appropriate handlers based on pattern
        data = callback.data
        
        if data.startswith("player_settings:"):
            await handle_player_controls_callback(bot_client, callback)
        elif data.startswith(("volume_", "loop_", "shuffle_", "player_back")):
            await handle_settings_callback(bot_client, callback)
        elif data.startswith("queue_"):
            await handle_queue_callback(bot_client, callback)
        else:
            await general_callback(bot_client, callback)
