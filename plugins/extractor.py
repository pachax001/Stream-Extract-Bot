"""Validate incoming video attachments before asking for extraction."""
from pathlib import Path
from html import escape

from wzgram import filters, Client
from wzgram.enums import ParseMode
from wzgram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from helpers.logger import logger
from helpers.progress import human_readable_bytes


@Client.on_message(filters.private & (filters.document | filters.video))
async def confirm_download(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    user_id = message.from_user.id
    if user_id not in Config.AUTH_USERS and user_id != Config.OWNER_ID:
        return

    media = message.document or message.video
    mime = (getattr(media, "mime_type", "") or "") if media else ""
    if not mime.startswith("video/"):
        await message.reply_text(
            "❌ Invalid media type. Please send a video file.",
            quote=True, disable_web_page_preview=True,
        )
        return

    fname = Path(getattr(media, "file_name", None) or "video").name
    size = human_readable_bytes(getattr(media, "file_size", 0) or 0)
    logger.info("User %s submitted video %s (%s)", user_id, fname, size)
    try:
        await message.reply_text(
            text=(
                f"File: <b>{escape(fname)}</b>\n"
                f"Size: <code>{size}</code>\n"
                "What would you like me to do?"
            ),
            parse_mode=ParseMode.HTML,
            quote=True,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("DOWNLOAD and PROCESS", callback_data="download_file")],
                [InlineKeyboardButton("CANCEL", callback_data="cancel")],
            ]),
        )
    except Exception:
        logger.exception("Unable to send video confirmation for user %s", user_id)
