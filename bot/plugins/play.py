"""
Music playback command handlers.
"""
import asyncio
import logging
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.errors import ChatAdminRequired

from bot.client import BotClient
from bot.helpers.localization import Localization
from bot.helpers.keyboards import KeyboardBuilder
from bot.helpers.formatting import Formatter
from bot.core.queue import Track

logger = logging.getLogger(__name__)


async def play_command(client: BotClient, message: Message):
    """Handle /play command."""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id if message.from_user else None
        
        # Check if this is a group chat (required for voice chats)
        if message.chat.type == "private":
            await message.reply(
                client.localization.get_text(chat_id, "error_messages.private_chat")
            )
            return
        
        # Check if user provided a query
        if not message.command or len(message.command) < 2:
            await message.reply(
                client.localization.get_text(chat_id, "invalid_input").format(command="play")
            )
            return
        
        query = " ".join(message.command[1:])
        
        # Send processing message
        processing_msg = await message.reply(
            client.localization.get_text(chat_id, "processing")
        )
        
        try:
            # Ensure assistant is setup for this chat
            if not await client.assistant_manager.setup_assistant_for_chat(chat_id):
                await processing_msg.edit_text(
                    client.localization.get_text(chat_id, "error_messages.chat_admin_required")
                )
                return
            
            # Start voice chat if needed
            if not await client.player.join_voice_chat(chat_id):
                await processing_msg.edit_text(
                    client.localization.get_text(chat_id, "error_messages.not_in_voice_chat")
                )
                return
            
            # Search or download music
            track_info = await client.youtube.handle_url(query)
            
            if not track_info:
                await processing_msg.edit_text(
                    client.localization.get_text(chat_id, "status_messages.invalid_search", query=query)
                )
                return
            
            # Create track object
            track = Track(
                file_path=track_info["file_path"],
                title=track_info["title"],
                artist=track_info["artist"],
                duration=track_info["duration"],
                thumbnail=track_info.get("thumbnail"),
                source_url=track_info.get("source_url"),
                added_by=user_id,
                metadata={
                    "video_id": track_info.get("video_id"),
                    "view_count": track_info.get("view_count", 0),
                    "description": track_info.get("description", "")
                }
            )
            
            # Add to queue
            queue_length = client.queue_manager.get_queue_length(chat_id)
            client.queue_manager.add_track(chat_id, track)
            
            # Format messages
            if queue_length == 0:
                # First track, start playing immediately
                success = await client.player.play_audio(chat_id, track.file_path)
                
                if success:
                    # Send now playing message
                    await client._update_now_playing_message(chat_id)
                    
                    # Start progress updater and auto-save
                    if chat_id in client.player.current_messages:
                        await client.player.start_progress_updater(
                            chat_id,
                            client.player.current_messages[chat_id],
                            client._update_now_playing_message
                        )
                    
                    await client.state_manager.start_auto_save(chat_id)
                    
                    added_text = client.formatter.format_added_to_queue(
                        track.to_dict(),
                        client.localization,
                        chat_id
                    )
                    await processing_msg.edit_text(
                        added_text + "\n\n🎵 <b>Now Playing!</b>",
                        reply_markup=client.keyboards.build_playback_controls(
                            chat_id,
                            True,
                            client.localization
                        )
                    )
                else:
                    await processing_msg.edit_text(
                        client.localization.get_text(chat_id, "error_messages.general_error", 
                                                    error="Failed to start playback")
                    )
            else:
                # Added to queue
                added_text = client.formatter.format_added_to_queue(
                    track.to_dict(),
                    client.localization,
                    chat_id
                )
                await processing_msg.edit_text(
                    added_text,
                    reply_markup=client.keyboards.build_queue_navigation(
                        chat_id,
                        0,  # First page
                        1,  # Will be updated
                        client.localization
                    ) if queue_length > 0 else None
                )
            
            logger.info(f"Added track to queue for chat {chat_id}: {track.title}")
            
        except Exception as e:
            logger.error(f"Error in play command for chat {chat_id}: {e}")
            await processing_msg.edit_text(
                client.localization.get_text(chat_id, "error_messages.general_error", error=str(e))
            )
        
    except Exception as e:
        logger.error(f"Error handling play command: {e}")
        if 'processing_msg' in locals():
            await processing_msg.edit_text(
                client.localization.get_text(chat_id, "error_messages.general_error", error=str(e))
            )


async def play_callback(client: BotClient, callback: CallbackQuery):
    """Handle play-related callbacks."""
    try:
        from bot.helpers.keyboards import KeyboardBuilder
        data = KeyboardBuilder.parse_callback_data(callback.data)
        
        chat_id = data.get("chat_id", 0)
        
        if not await _verify_callback_access(client, callback, chat_id):
            return
        
        action = data["action"]
        
        if action == "player_back":
            # Return to player view
            await client._update_now_playing_message(chat_id)
            await callback.answer("Returned to player")
            
        elif action == "player_pause":
            # Pause playback
            if await client.player.pause_playback(chat_id):
                # Update message
                await client._update_now_playing_message(chat_id)
                await callback.answer(
                    client.localization.get_text(chat_id, "status_messages.playback_paused")
                )
            else:
                await callback.answer(
                    client.localization.get_text(chat_id, "error_messages.no_active_playback")
                )
                
        elif action == "player_play":
            # Resume playback
            if await client.player.resume_playback(chat_id):
                # Update message
                await client._update_now_playing_message(chat_id)
                await callback.answer(
                    client.localization.get_text(chat_id, "status_messages.playback_resumed")
                )
            else:
                await callback.answer(
                    client.localization.get_text(chat_id, "error_messages.no_active_playback")
                )
        
        elif action == "player_skip":
            # Skip current track
            await _handle_skip(client, chat_id, callback)
            
        elif action == "player_stop":
            # Stop playback
            await _handle_stop(client, chat_id, callback)
        
    except Exception as e:
        logger.error(f"Error handling play callback: {e}")
        await callback.answer("❌ An error occurred")


async def _handle_skip(client: BotClient, chat_id: int, callback: CallbackQuery):
    """Handle track skipping."""
    try:
        # Skip current track
        await client.player.skip_track(chat_id)
        
        # Get next track
        next_track = client.queue_manager.get_next_track(chat_id)
        
        if next_track:
            # Start next track
            success = await client.player.play_audio(chat_id, next_track.file_path)
            
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
                
                await callback.answer(
                    client.localization.get_text(chat_id, "status_messages.track_skipped")
                )
            else:
                await callback.answer("Failed to start next track")
        else:
            # No more tracks
            await client.player.stop_playback(chat_id)
            await callback.answer("Queue finished")
        
    except Exception as e:
        logger.error(f"Error handling skip for chat {chat_id}: {e}")
        await callback.answer("❌ Error skipping track")


async def _handle_stop(client: BotClient, chat_id: int, callback: CallbackQuery):
    """Handle playback stop."""
    try:
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
        
        await callback.answer(
            client.localization.get_text(chat_id, "status_messages.track_skipped")
        )
        
    except Exception as e:
        logger.error(f"Error handling stop for chat {chat_id}: {e}")
        await callback.answer("❌ Error stopping playback")


async def _verify_callback_access(client: BotClient, callback: CallbackQuery, chat_id: int) -> bool:
    """Verify callback access (basic check)."""
    try:
        # For now, allow all callbacks
        # In production, you might want to add rate limiting or admin checks
        return True
    except Exception as e:
        logger.error(f"Error verifying callback access: {e}")
        return False


def register_handlers(app: Client, bot_client: BotClient):
    """Register all play handlers."""
    
    @app.on_message(filters.command("play"))
    async def handle_play(client: Client, message: Message):
        await play_command(bot_client, message)
    
    @app.on_callback_query(filters.regex("^player_.*"))
    async def handle_play_callback(client: Client, callback: CallbackQuery):
        await play_callback(bot_client, callback)
