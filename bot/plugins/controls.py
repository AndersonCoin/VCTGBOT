"""
Playback control command handlers.
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

from bot.client import BotClient
from bot.helpers.localization import Localization

logger = logging.getLogger(__name__)


async def pause_command(client: BotClient, message: Message):
    """Handle /pause command."""
    try:
        chat_id = message.chat.id
        
        # Check if bot is playing
        if not client.player.is_playing(chat_id):
            await message.reply(
                client.localization.get_text(chat_id, "error_messages.no_active_playback")
            )
            return
        
        # Pause playback
        success = await client.player.pause_playback(chat_id)
        
        if success:
            # Update now playing message
            await client._update_now_playing_message(chat_id)
            
            await message.reply(
                client.localization.get_text(chat_id, "status_messages.playback_paused")
            )
        else:
            await message.reply(
                client.localization.get_text(chat_id, "error_messages.general_error", error="Failed to pause")
            )
        
    except Exception as e:
        logger.error(f"Error handling pause command: {e}")
        await message.reply(
            client.localization.get_text(0, "error_messages.general_error", error=str(e))
        )


async def resume_command(client: BotClient, message: Message):
    """Handle /resume command."""
    try:
        chat_id = message.chat.id
        
        # Check if there's saved state to resume
        saved_state = await client.state_manager.get_playback_state(chat_id)
        
        if saved_state:
            # Resume from saved state
            track_info = saved_state.get("track", {})
            position = saved_state.get("restored_position", 0)
            
            success = await client.player.play_audio(
                chat_id, 
                track_info.get("file_path", ""),
                resume_from=position
            )
            
            if success:
                # Start progress updater
                if chat_id in client.player.current_messages:
                    await client.player.start_progress_updater(
                        chat_id,
                        client.player.current_messages[chat_id],
                        client._update_now_playing_message
                    )
                
                await client.state_manager.start_auto_save(chat_id)
                
                await message.reply(
                    client.localization.get_text(chat_id, "status_messages.playback_resumed")
                )
            else:
                await message.reply(
                    client.localization.get_text(chat_id, "error_messages.general_error", error="Failed to resume")
                )
        else:
            # Check if bot is paused
            if not client.player.is_playing(chat_id):
                success = await client.player.resume_playback(chat_id)
                
                if success:
                    await client._update_now_playing_message(chat_id)
                    await message.reply(
                        client.localization.get_text(chat_id, "status_messages.playback_resumed")
                    )
                else:
                    await message.reply(
                        client.localization.get_text(chat_id, "error_messages.no_active_playback")
                    )
            else:
                await message.reply(
                    client.localization.get_text(chat_id, "error_messages.general_error", error="Already playing")
                )
        
    except Exception as e:
        logger.error(f"Error handling resume command: {e}")
        await message.reply(
            client.localization.get_text(0, "error_messages.general_error", error=str(e))
        )


async def stop_command(client: BotClient, message: Message):
    """Handle /stop command."""
    try:
        chat_id = message.chat.id
        
        # Check admin privileges for stop command
        if not await _check_admin_privileges(client, message):
            return
        
        # Stop playback and leave voice chat
        await client.player.stop_playback(chat_id)
        await client.player.leave_voice_chat(chat_id)
        
        # Stop auto-save
        await client.state_manager.stop_auto_save(chat_id)
        
        # Clear queue
        client.queue_manager.clear_queue(chat_id)
        
        await message.reply(
            client.localization.get_text(chat_id, "status_messages.left_voice_chat")
        )
        
    except Exception as e:
        logger.error(f"Error handling stop command: {e}")
        await message.reply(
            client.localization.get_text(0, "error_messages.general_error", error=str(e))
        )


async def skip_command(client: BotClient, message: Message):
    """Handle /skip command."""
    try:
        chat_id = message.chat.id
        
        # Check if there's an active playback
        if not client.player.is_playing(chat_id):
            await message.reply(
                client.localization.get_text(chat_id, "error_messages.no_active_playback")
            )
            return
        
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
                
                await message.reply(
                    client.localization.get_text(chat_id, "status_messages.track_skipped")
                )
            else:
                await message.reply(
                    client.localization.get_text(chat_id, "error_messages.general_error", error="Failed to start next track")
                )
        else:
            # No more tracks, stop playback
            await client.player.stop_playback(chat_id)
            await client.player.leave_voice_chat(chat_id)
            
            # Stop auto-save
            await client.state_manager.stop_auto_save(chat_id)
            
            # Clear queue
            client.queue_manager.clear_queue(chat_id)
            
            await message.reply("🎵 Queue finished!")
        
    except Exception as e:
        logger.error(f"Error handling skip command: {e}")
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


async def controls_callback(client: BotClient, callback: CallbackQuery):
    """Handle control-related callbacks."""
    try:
        from bot.helpers.keyboards import KeyboardBuilder
        data = KeyboardBuilder.parse_callback_data(callback.data)
        
        chat_id = data.get("chat_id", 0)
        
        # Verify callback access
        if not await _verify_callback_access(client, callback, chat_id):
            return
        
        action = data["action"]
        
        if action == "volume_up":
            await callback.answer("Volume control not implemented yet")
            
        elif action == "volume_down":
            await callback.answer("Volume control not implemented yet")
            
        elif action == "loop_toggle":
            # Toggle loop mode
            current_loop = client.queue_manager.is_looping(chat_id)
            client.queue_manager.set_loop_mode(chat_id, not current_loop)
            
            status = "enabled" if not current_loop else "disabled"
            await callback.answer(f"Loop mode {status}")
            
            # Update settings menu
            await _update_settings_menu(client, chat_id, callback)
            
        elif action == "shuffle_queue":
            # Shuffle queue
            success = client.queue_manager.shuffle_queue(chat_id)
            
            if success:
                await callback.answer("Queue shuffled!")
            else:
                await callback.answer("Cannot shuffle queue")
            
            # Update settings menu
            await _update_settings_menu(client, chat_id, callback)
            
        elif action == "player_back":
            # Return to player view
            await client._update_now_playing_message(chat_id)
            await callback.answer("Returned to player")
            
    except Exception as e:
        logger.error(f"Error handling controls callback: {e}")
        await callback.answer("❌ An error occurred")


async def _update_settings_menu(client: BotClient, chat_id: int, callback: CallbackQuery):
    """Update settings menu message."""
    try:
        settings_keyboard = client.keyboards.build_settings_menu(chat_id, client.localization)
        
        await callback.message.edit_reply_markup(settings_keyboard)
        
    except Exception as e:
        logger.error(f"Error updating settings menu: {e}")


async def _verify_callback_access(client: BotClient, callback: CallbackQuery, chat_id: int) -> bool:
    """Verify callback access."""
    try:
        # Basic rate limiting check could be added here
        return True
    except Exception as e:
        logger.error(f"Error verifying callback access: {e}")
        return False


def register_handlers(app: Client, bot_client: BotClient):
    """Register all control handlers."""
    
    @app.on_message(filters.command("pause"))
    async def handle_pause(client: Client, message: Message):
        await pause_command(bot_client, message)
    
    @app.on_message(filters.command("resume"))
    async def handle_resume(client: Client, message: Message):
        await resume_command(bot_client, message)
    
    @app.on_message(filters.command("stop"))
    async def handle_stop(client: Client, message: Message):
        await stop_command(bot_client, message)
    
    @app.on_message(filters.command("skip"))
    async def handle_skip(client: Client, message: Message):
        await skip_command(bot_client, message)
    
    @app.on_callback_query(filters.regex("^(volume_|loop_|shuffle_|player_back)"))
    async def handle_controls_callback(client: Client, callback: CallbackQuery):
        await controls_callback(bot_client, callback)
