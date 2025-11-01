"""
Start and help command handlers.
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

from bot.client import BotClient
from bot.helpers.localization import Localization
from bot.helpers.keyboards import KeyboardBuilder

logger = logging.getLogger(__name__)


async def start_command(client: BotClient, message: Message):
    """Handle /start command."""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id if message.from_user else None
        
        # Set default language if not set
        if user_id:
            client.localization.set_user_language(chat_id, "en")
        
        # Send welcome message
        welcome_text = client.localization.get_text(chat_id, "start_message")
        
        # Build language selection keyboard
        current_lang = client.localization.get_user_language(chat_id)
        language_keyboard = client.keyboards.build_language_selection(
            current_lang, 
            client.localization
        )
        
        await message.reply(
            welcome_text,
            reply_markup=language_keyboard,
            disable_web_page_preview=True
        )
        
        logger.info(f"Start command from chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error handling start command: {e}")
        await message.reply("❌ An error occurred. Please try again later.")


async def help_command(client: BotClient, message: Message):
    """Handle /help command."""
    try:
        chat_id = message.chat.id
        
        # Get help text
        help_text = client.localization.get_text(chat_id, "help_message")
        
        # Build language selection keyboard
        current_lang = client.localization.get_user_language(chat_id)
        language_keyboard = client.keyboards.build_language_selection(
            current_lang, 
            client.localization
        )
        
        await message.reply(
            help_text,
            reply_markup=language_keyboard,
            disable_web_page_preview=True
        )
        
        logger.info(f"Help command from chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error handling help command: {e}")
        await message.reply("❌ An error occurred. Please try again later.")


async def language_command(client: BotClient, message: Message):
    """Handle /language command."""
    try:
        chat_id = message.chat.id
        
        # Get current language
        current_lang = client.localization.get_user_language(chat_id)
        
        # Send language selection message
        lang_text = client.localization.get_text(chat_id, "language_select")
        current_text = client.localization.get_text(
            chat_id, 
            "language_current",
            lang="English" if current_lang == "en" else "العربية"
        )
        
        full_text = f"{lang_text}\n\n{current_text}"
        
        # Build language selection keyboard
        language_keyboard = client.keyboards.build_language_selection(
            current_lang, 
            client.localization
        )
        
        await message.reply(
            full_text,
            reply_markup=language_keyboard
        )
        
        logger.info(f"Language command from chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error handling language command: {e}")
        await message.reply("❌ An error occurred. Please try again later.")


async def language_callback(client: BotClient, callback: CallbackQuery):
    """Handle language selection callback."""
    try:
        chat_id = callback.message.chat.id
        user_id = callback.from_user.id
        
        # Parse callback data
        from bot.helpers.keyboards import KeyboardBuilder
        data = KeyboardBuilder.parse_callback_data(callback.data)
        
        if data["action"] == "lang_set" and len(data["params"]) > 0:
            selected_lang = data["params"][0]
            
            # Set user language
            client.localization.set_user_language(chat_id, selected_lang)
            
            # Get language name for confirmation
            lang_names = {
                "en": "English",
                "ar": "العربية"
            }
            lang_name = lang_names.get(selected_lang, selected_lang)
            
            # Send confirmation
            confirm_text = client.localization.get_text(
                chat_id, 
                "language_updated",
                lang=lang_name
            )
            
            # Update the message
            await callback.message.edit_text(
                confirm_text,
                reply_markup=None
            )
            
            # Answer callback
            await callback.answer(confirm_text)
            
            logger.info(f"Language changed to {selected_lang} for chat {chat_id}")
        else:
            await callback.answer("Invalid language selection")
        
    except Exception as e:
        logger.error(f"Error handling language callback: {e}")
        await callback.answer("❌ An error occurred")


def register_handlers(app: Client, bot_client: BotClient):
    """Register all handlers."""
    
    @app.on_message(filters.command("start"))
    async def handle_start(client: Client, message: Message):
        await start_command(bot_client, message)
    
    @app.on_message(filters.command("help"))
    async def handle_help(client: Client, message: Message):
        await help_command(bot_client, message)
    
    @app.on_message(filters.command("language"))
    async def handle_language(client: Client, message: Message):
        await language_command(bot_client, message)
    
    @app.on_callback_query(filters.regex("^lang_set:"))
    async def handle_language_callback(client: Client, callback: CallbackQuery):
        await language_callback(bot_client, callback)
