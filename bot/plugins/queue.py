"""
Queue management command handlers.
"""
import logging
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

from bot.client import BotClient
from bot.helpers.localization import Localization
from bot.helpers.keyboards import KeyboardBuilder
from bot.helpers.formatting import Formatter

logger = logging.getLogger(__name__)


async def queue_command(client: BotClient, message: Message):
    """Handle /queue command."""
    try:
        chat_id = message.chat.id
        
        # Get queue information
        queue_info = client.queue_manager.get_queue_info(chat_id)
        total_tracks = queue_info["total_tracks"]
        
        if total_tracks == 0:
            # Queue is empty
            empty_text = client.localization.get_text(chat_id, "queue_empty")
            await message.reply(empty_text)
            return
        
        # Calculate pagination
        page = 0
        page_size = 10
        
        # Get current page
        page_data = client.queue_manager.get_page(chat_id, page, page_size)
        
        # Format queue header
        queue_header = client.formatter.format_queue_header(
            queue_info,
            client.localization,
            chat_id
        )
        
        # Build queue list
        queue_text = await _format_queue_list(
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
        
        # Combine header and list
        full_text = f"{queue_header}\n\n{queue_text}"
        
        await message.reply(
            full_text,
            reply_markup=queue_keyboard,
            disable_web_page_preview=True
        )
        
        logger.info(f"Queue command from chat {chat_id}, {total_tracks} tracks")
        
    except Exception as e:
        logger.error(f"Error handling queue command: {e}")
        await message.reply(
            client.localization.get_text(0, "error_messages.general_error", error=str(e))
        )


async def queue_callback(client: BotClient, callback: CallbackQuery):
    """Handle queue-related callbacks."""
    try:
        from bot.helpers.keyboards import KeyboardBuilder
        data = KeyboardBuilder.parse_callback_data(callback.data)
        
        chat_id = data.get("chat_id", 0)
        
        # Verify callback access
        if not await _verify_callback_access(client, callback, chat_id):
            return
        
        action = data["action"]
        
        if action == "queue_open":
            # Open queue view
            page = data.get("page", 0)
            await _show_queue_page(client, chat_id, page, callback)
            
        elif action == "queue_nav":
            # Navigate queue pages
            page = data.get("page", 0)
            await _show_queue_page(client, chat_id, page, callback)
            
        elif action == "queue_skip":
            # Skip to specific track
            index = data.get("index", 0)
            await _skip_to_track(client, chat_id, index, callback)
            
        elif action == "queue_refresh":
            # Refresh queue view
            await queue_callback(client, callback)  # Recursively call with updated data
        
    except Exception as e:
        logger.error(f"Error handling queue callback: {e}")
        await callback.answer("❌ An error occurred")


async def _show_queue_page(client: BotClient, chat_id: int, page: int, callback: CallbackQuery):
    """Show queue page."""
    try:
        # Get queue information
        queue_info = client.queue_manager.get_queue_info(chat_id)
        total_tracks = queue_info["total_tracks"]
        
        if total_tracks == 0:
            empty_text = client.localization.get_text(chat_id, "queue_empty")
            await callback.message.edit_text(empty_text)
            return
        
        # Get page data
        page_data = client.queue_manager.get_page(chat_id, page)
        
        # Format queue header
        queue_header = client.formatter.format_queue_header(
            queue_info,
            client.localization,
            chat_id
        )
        
        # Build queue list
        queue_text = await _format_queue_list(
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
        
        await callback.answer(f"Page {page + 1} of {page_data['total_pages']}")
        
    except Exception as e:
        logger.error(f"Error showing queue page: {e}")
        await callback.answer("❌ Error loading queue")


async def _format_queue_list(
    client: BotClient, 
    tracks: list, 
    current_index: int, 
    page: int, 
    chat_id: int
) -> str:
    """Format queue track list."""
    try:
        if not tracks:
            return "No tracks in this page."
        
        queue_lines = []
        
        for i, track in enumerate(tracks):
            global_index = page * 10 + i  # Assuming 10 tracks per page
            
            # Format track info
            title = client.formatter.sanitize_text(track.title, 40)
            artist = client.formatter.sanitize_text(track.artist, 30)
            duration = client.formatter.format_duration(track.duration, client.localization, chat_id)
            
            # Add current track indicator
            if global_index == current_index:
                indicator = "▶️ "
                format_type = "bold"
            else:
                indicator = "  "
                format_type = "plain"
            
            # Format line
            line = f"{indicator}{global_index + 1}. **{title}**\n   👤 {artist} • ⏱️ {duration}"
            
            # For current track, add position
            if global_index == current_index and client.player:
                current_pos = int(client.player.get_current_position(chat_id))
                pos_str = client.formatter.format_duration(current_pos, client.localization, chat_id)
                line += f" ({pos_str})"
            
            queue_lines.append(line)
        
        return "\n\n".join(queue_lines)
        
    except Exception as e:
        logger.error(f"Error formatting queue list: {e}")
        return "Error formatting queue list."


async def _skip_to_track(client: BotClient, chat_id: int, index: int, callback: CallbackQuery):
    """Skip to specific track in queue."""
    try:
        # Check if index is valid
        queue_length = client.queue_manager.get_queue_length(chat_id)
        if index < 0 or index >= queue_length:
            await callback.answer("Invalid track index")
            return
        
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
            
            await callback.answer(f"Playing track {index + 1}: {track.title[:30]}...")
        else:
            await callback.answer("Failed to play track")
        
    except Exception as e:
        logger.error(f"Error skipping to track: {e}")
        await callback.answer("❌ Error skipping to track")


async def clear_queue_command(client: BotClient, message: Message):
    """Handle /clear command."""
    try:
        chat_id = message.chat.id
        
        # Check admin privileges
        if not await _check_admin_privileges(client, message):
            return
        
        # Clear queue
        client.queue_manager.clear_queue(chat_id)
        
        # Stop current playback if any
        if client.player.is_playing(chat_id):
            await client.player.stop_playback(chat_id)
        
        await message.reply(
            client.localization.get_text(chat_id, "status_messages.queue_cleared")
        )
        
    except Exception as e:
        logger.error(f"Error handling clear queue command: {e}")
        await message.reply(
            client.localization.get_text(0, "error_messages.general_error", error=str(e))
        )


async def shuffle_queue_command(client: BotClient, message: Message):
    """Handle /shuffle command."""
    try:
        chat_id = message.chat.id
        
        # Shuffle queue
        success = client.queue_manager.shuffle_queue(chat_id)
        
        if success:
            await message.reply("🔀 Queue shuffled!")
        else:
            await message.reply("❌ Cannot shuffle queue (need at least 2 tracks)")
        
    except Exception as e:
        logger.error(f"Error handling shuffle command: {e}")
        await message.reply(
            client.localization.get_text(0, "error_messages.general_error", error=str(e))
        )


async def _check_admin_privileges(client: BotClient, message: Message) -> bool:
    """Check if user has admin privileges."""
    try:
        if message.chat.type == "private":
            return False
        
        # Get chat member info
        chat_member = await client.bot.get_chat_member(
            message.chat.id, 
            message.from_user.id
        )
        
        # Check if user is admin or owner
        if chat_member.status in ["administrator", "owner"]:
            return True
        
        # Send admin required message
        message.reply(
            client.localization.get_text(message.chat.id, "admin_only")
        )
        return False
        
    except Exception as e:
        logger.error(f"Error checking admin privileges: {e}")
        return False


async def _verify_callback_access(client: BotClient, callback: CallbackQuery, chat_id: int) -> bool:
    """Verify callback access."""
    try:
        # Basic rate limiting check could be added here
        return True
    except Exception as e:
        logger.error(f"Error verifying callback access: {e}")
        return False


def register_handlers(app: Client, bot_client: BotClient):
    """Register all queue handlers."""
    
    @app.on_message(filters.command("queue"))
    async def handle_queue(client: Client, message: Message):
        await queue_command(bot_client, message)
    
    @app.on_message(filters.command("clear"))
    async def handle_clear(client: Client, message: Message):
        await clear_queue_command(bot_client, message)
    
    @app.on_message(filters.command("shuffle"))
    async def handle_shuffle(client: Client, message: Message):
        await shuffle_queue_command(bot_client, message)
    
    @app.on_callback_query(filters.regex("^queue_.*"))
    async def handle_queue_callback(client: Client, callback: CallbackQuery):
        await queue_callback(bot_client, callback)
