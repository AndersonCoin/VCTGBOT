"""
Assistant management helper for auto-invite and promotion.
"""
import asyncio
import logging
from typing import Optional

from pyrogram import Client
from pyrogram.errors import (
    UserNotParticipant, 
    ChatAdminRequired, 
    UserPrivacyRestricted,
    ChatAdminPrivilegesRequired,
    PeerIdInvalid
)
from pyrogram.types import ChatPrivileges

logger = logging.getLogger(__name__)


class AssistantManager:
    """Manages assistant user operations."""
    
    def __init__(self, assistant_username: str, bot: Client, assistant: Client):
        """Initialize assistant manager."""
        self.assistant_username = assistant_username
        self.bot = bot
        self.assistant = assistant
    
    async def ensure_assistant_in_chat(self, chat_id: int) -> bool:
        """Ensure assistant is member of chat."""
        try:
            # Get chat member info for assistant
            member = await self.bot.get_chat_member(chat_id, self.assistant_username)
            
            if member.status == "left":
                # Assistant is not in chat, invite them
                logger.info(f"Assistant not in chat {chat_id}, inviting...")
                return await self._invite_assistant(chat_id)
            elif member.status == "kicked":
                # Assistant was kicked, need to be re-invited
                logger.info(f"Assistant was kicked from chat {chat_id}, re-inviting...")
                return await self._invite_assistant(chat_id)
            else:
                # Assistant is already in chat
                logger.info(f"Assistant already in chat {chat_id}")
                return True
                
        except UserNotParticipant:
            logger.info(f"Assistant not participant in chat {chat_id}, inviting...")
            return await self._invite_assistant(chat_id)
        except ChatAdminRequired:
            logger.error(f"Bot needs admin rights to invite assistant in chat {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to check assistant status in chat {chat_id}: {e}")
            return False
    
    async def _invite_assistant(self, chat_id: int) -> bool:
        """Invite assistant to chat."""
        try:
            # Try to add assistant via bot
            await self.bot.add_chat_members(chat_id, [self.assistant_username])
            logger.info(f"Assistant invited to chat {chat_id}")
            return True
            
        except ChatAdminRequired:
            logger.error(f"Bot needs admin rights to invite members in chat {chat_id}")
            return False
        except UserPrivacyRestricted:
            logger.warning(f"Assistant has privacy restrictions in chat {chat_id}")
            # Try to get the assistant's invite link or send a join request
            return await self._handle_privacy_restriction(chat_id)
        except Exception as e:
            logger.error(f"Failed to invite assistant to chat {chat_id}: {e}")
            return False
    
    async def _handle_privacy_restriction(self, chat_id: int) -> bool:
        """Handle assistant privacy restrictions."""
        try:
            # Try to get assistant's public username or link
            assistant_user = await self.bot.get_users(self.assistant_username)
            
            # Send message explaining situation
            await self.bot.send_message(
                chat_id,
                f"🤖 The music assistant (@{self.assistant_username}) has privacy restrictions.\n\n"
                "To use the music bot, please:\n"
                "1. Add @{} to the chat manually, or\n"
                "2. Ask the assistant to disable their privacy settings".format(self.assistant_username)
            )
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to handle privacy restriction: {e}")
            return False
    
    async def promote_assistant(self, chat_id: int) -> bool:
        """Promote assistant with necessary privileges."""
        try:
            # Get assistant user ID
            assistant_user = await self.bot.get_users(self.assistant_username)
            assistant_id = assistant_user.id
            
            # Define required privileges
            privileges = ChatPrivileges(
                can_manage_video_chats=True,
                can_manage_chat=True,
                can_change_info=False,
                can_delete_messages=False,
                can_invite_users=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_promote_members=False
            )
            
            # Promote assistant
            await self.bot.set_chat_member(
                chat_id,
                assistant_id,
                privileges
            )
            
            logger.info(f"Promoted assistant in chat {chat_id}")
            return True
            
        except ChatAdminRequired:
            logger.error(f"Bot needs admin rights to promote members in chat {chat_id}")
            return False
        except ChatAdminPrivilegesRequired:
            logger.error(f"Bot needs admin privileges to promote members in chat {chat_id}")
            return False
        except UserNotParticipant:
            logger.error(f"Assistant is not in chat {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to promote assistant in chat {chat_id}: {e}")
            return False
    
    async def demote_assistant(self, chat_id: int) -> bool:
        """Remove assistant privileges."""
        try:
            assistant_user = await self.bot.get_users(self.assistant_username)
            assistant_id = assistant_user.id
            
            # Remove all privileges
            privileges = ChatPrivileges(
                can_manage_video_chats=False,
                can_manage_chat=False,
                can_change_info=False,
                can_delete_messages=False,
                can_invite_users=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_promote_members=False
            )
            
            await self.bot.set_chat_member(
                chat_id,
                assistant_id,
                privileges
            )
            
            logger.info(f"Demoted assistant in chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to demote assistant in chat {chat_id}: {e}")
            return False
    
    async def check_bot_admin_status(self, chat_id: int) -> bool:
        """Check if bot has admin rights in chat."""
        try:
            bot_member = await self.bot.get_chat_member(chat_id, "me")
            return bot_member.status in ["administrator", "owner"]
        except Exception as e:
            logger.error(f"Failed to check bot admin status in chat {chat_id}: {e}")
            return False
    
    async def get_required_admin_rights(self) -> dict:
        """Get list of required admin rights."""
        return {
            "can_manage_video_chats": True,
            "can_manage_chat": True,
            "can_change_info": False,
            "can_delete_messages": False,
            "can_invite_users": True,
            "can_restrict_members": False,
            "can_pin_messages": False,
            "can_promote_members": False
        }
    
    async def setup_assistant_for_chat(self, chat_id: int) -> bool:
        """Complete setup: ensure assistant is member and promoted."""
        try:
            # Check bot admin status first
            if not await self.check_bot_admin_status(chat_id):
                logger.error(f"Bot needs admin rights in chat {chat_id}")
                return False
            
            # Ensure assistant is in chat
            if not await self.ensure_assistant_in_chat(chat_id):
                logger.error(f"Failed to ensure assistant in chat {chat_id}")
                return False
            
            # Wait a bit for assistant to join
            await asyncio.sleep(2)
            
            # Try to promote assistant
            if not await self.promote_assistant(chat_id):
                logger.warning(f"Could not promote assistant in chat {chat_id}")
                # Not a critical error, assistant might work without promotion
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup assistant for chat {chat_id}: {e}")
            return False
    
    async def send_setup_instructions(self, chat_id: int) -> bool:
        """Send setup instructions to chat."""
        try:
            instructions = (
                "🤖 **Music Bot Setup Instructions**\n\n"
                "To use the music bot, I need the following:\n\n"
                "1️⃣ **Admin Rights for Bot:**\n"
                "   • Make the bot an administrator\n"
                "   • Grant 'Manage Video Chats' permission\n"
                "   • Allow adding members\n\n"
                "2️⃣ **Add Music Assistant:**\n"
                f"   • Add @{self.assistant_username} to the chat\n"
                "   • Grant 'Manage Video Chats' permission\n\n"
                "3️⃣ **Start Voice Chat:**\n"
                "   • Start a group voice chat\n"
                "   • Use /play to start playing music\n\n"
                "Once completed, you can enjoy music playback!"
            )
            
            await self.bot.send_message(chat_id, instructions)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send setup instructions to chat {chat_id}: {e}")
            return False
    
    async def cleanup_assistant_from_chat(self, chat_id: int) -> bool:
        """Clean up assistant from chat (optional)."""
        try:
            # This could be used to leave the chat when done
            # But we might want to keep them for future use
            
            # For now, just log
            logger.info(f"Cleaning up assistant from chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup assistant from chat {chat_id}: {e}")
            return False
