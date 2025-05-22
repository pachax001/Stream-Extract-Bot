import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from script import Script
from helpers.logger import logger
from helpers.progress import human_readable_bytes


@Client.on_message(filters.private & (filters.document | filters.video))
async def confirm_download(client: Client, message: Message) -> None:
    """
    Prompt the user to confirm download and processing of a video file.
    """
    user_id = message.from_user.id
    # Authorization check
    if user_id not in Config.AUTH_USERS and user_id != Config.OWNER_ID:
        return

    media = message.document or message.video
    mime = getattr(media, "mime_type", "")

    # Only accept video files
    if mime.startswith("video/"):
        fname = getattr(media, "file_name", "<unknown>")
        fsize = getattr(media, "file_size", 0)
        size_str = human_readable_bytes(fsize)

        logger.info(f"User {user_id} requested to download {fname} ({size_str})")
        await asyncio.sleep(1)

        await message.reply_text(
            text=(f"**{Script.start_msg('')}**\n"  # You can customize prompt text here
                  f"File: **{fname}**\n"
                  f"Size: `{size_str}`\n"
                  "What would you like me to do?"),
            quote=True,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("DOWNLOAD and PROCESS", callback_data="download_file")],
                [InlineKeyboardButton("CANCEL", callback_data="cancel")]
            ])
        )
    else:
        await message.reply_text(
            text="❌ Invalid media type. Please send a video file.",
            quote=True,
            disable_web_page_preview=True
        )