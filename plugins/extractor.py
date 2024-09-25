from pyrogram import filters
from pyrogram import Client as trojanz
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


from config import Config
from script import Script
from helpers.logger import logger
from helpers.progress import humanbytes
from pyrogram.enums import ParseMode
import pyrogram.errors as perrors
import asyncio


@trojanz.on_message(filters.private & (filters.document | filters.video))
async def confirm_dwnld(client, message):

    if message.from_user.id not in Config.AUTH_USERS and message.from_user.id != Config.OWNER_ID:
        return

    media = message
    filetype = media.document or media.video

    if filetype.mime_type.startswith("video/"):
        user_id = message.from_user.id  # Set the user ID
        try:
            user_first_name = message.from_user.first_name  # Set the first name
        except:
            user_first_name = "Unknown"

        await asyncio.sleep(2)
        logger.info(f"User {user_id} - {user_first_name} requested to download a video")

        await message.reply_text(
            "**What you want me to do??**",
            quote=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    text="DOWNLOAD and PROCESS", callback_data="download_file")],
                [InlineKeyboardButton(text="CANCEL", callback_data="close")]
            ])
        )
        
    else:
        await message.reply_text(
            "Invalid Media",
            quote=True
        )
