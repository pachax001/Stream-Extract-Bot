"""Upload extracted streams and optionally mirror them to a log channel."""
import html
import time
from pathlib import Path
from typing import Any

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from wzgram import Client
from wzgram.enums import ParseMode
from wzgram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from helpers.logger import logger
from helpers.progress import progress_func, upload_progress, callback_progress
from helpers.tools import clean_up

LOG_CHANNEL_ID = Config.LOG_CHANNEL
BOT_USERNAME = Config.BOT_USERNAME


def _extract_metadata(file_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"title": None, "artist": None, "duration": 0}
    try:
        parser = createParser(str(file_path))
        if parser is None:
            return result
        try:
            metadata = extractMetadata(parser)
            if metadata:
                for key in ("title", "artist"):
                    if metadata.has(key):
                        result[key] = metadata.get(key)
                if metadata.has("duration"):
                    result["duration"] = int(metadata.get("duration").total_seconds())
        finally:
            parser.close()
    except Exception:
        logger.exception("Could not read metadata for %s", file_path)
    return result


async def _common_upload_logic(
    client: Client,
    original_message: Message,
    file_loc: str,
    file_name_display: str,
    user_id: int,
    username: str,
    upload_type: str,
) -> bool:
    """Report success only after Telegram confirms delivery to the requesting user."""
    file_path = Path(file_loc)
    upload_key = f"{original_message.chat.id}_{original_message.id}_ul"
    status_msg = None
    try:
        if not file_path.is_file() or file_path.stat().st_size == 0:
            logger.error("Upload output is missing or empty: %s", file_path)
            await original_message.edit_text("❌ Extracted output file is unavailable.")
            return False

        status_msg = await original_message.edit_text(
            text=f"Uploading {upload_type}: {file_name_display}",
            parse_mode=ParseMode.DISABLED,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Progress", callback_data=f"progress_msg_{upload_key}")
            ]]),
        )

        metadata = _extract_metadata(file_path) if upload_type == "audio" else {}
        progress_args = (
            "ul", status_msg, time.monotonic(), original_message,
            file_name_display, 3.0, {},
        )
        caption = f"Uploaded by @{BOT_USERNAME}\nFile: {file_name_display}"
        if upload_type == "audio":
            sent = await client.send_audio(
                chat_id=original_message.chat.id,
                audio=file_loc,
                caption=caption,
                parse_mode=ParseMode.DISABLED,
                title=metadata.get("title") or file_name_display,
                performer=metadata.get("artist"),
                duration=metadata.get("duration"),
                progress=progress_func,
                progress_args=progress_args,
            )
        elif upload_type == "subtitle":
            sent = await client.send_document(
                chat_id=original_message.chat.id,
                document=file_loc,
                caption=caption,
                parse_mode=ParseMode.DISABLED,
                progress=progress_func,
                progress_args=progress_args,
            )
        else:
            raise ValueError(f"Unknown upload type: {upload_type}")

        if sent is None:
            raise RuntimeError("Telegram returned no sent message")

        # Logging is best-effort. A failure to send to a log channel must not
        # report a failed upload when the user has already received the file.
        if LOG_CHANNEL_ID:
            log_caption = (
                f"Extracted by: <a href=\"tg://user?id={user_id}\">"
                f"{html.escape(username)}</a>\nFile: {html.escape(file_name_display)}"
            )
            try:
                if upload_type == "audio":
                    await client.send_audio(
                        chat_id=int(LOG_CHANNEL_ID), audio=file_loc,
                        caption=log_caption, parse_mode=ParseMode.HTML,
                        title=metadata.get("title") or file_name_display,
                        performer=metadata.get("artist"),
                        duration=metadata.get("duration"),
                    )
                else:
                    await client.send_document(
                        chat_id=int(LOG_CHANNEL_ID), document=file_loc,
                        caption=log_caption, parse_mode=ParseMode.HTML,
                    )
            except Exception:
                logger.exception("Could not mirror %s to log channel %s", file_name_display, LOG_CHANNEL_ID)

        try:
            await status_msg.delete()
        except Exception:
            logger.exception("Could not delete finished upload status message")
        logger.info("Successfully delivered %s to user=%s", file_name_display, user_id)
        return True
    except Exception:
        logger.exception("Upload failed for %s user=%s", file_name_display, user_id)
        try:
            await original_message.edit_text(
                "❌ Upload failed. Please send the original video again."
            )
        except Exception:
            logger.exception("Could not report failed upload")
        return False
    finally:
        upload_progress.pop(upload_key, None)
        if status_msg:
            callback_progress.pop(f"{status_msg.chat.id}_{status_msg.id}_callback", None)
        await clean_up(file_path)


async def upload_audio(
    client: Client, message: Message, file_loc: str,
    username: str, user_id: int, file_name: str
) -> bool:
    return await _common_upload_logic(
        client, message, file_loc, file_name, user_id, username, "audio"
    )


async def upload_subtitle(
    client: Client, message: Message, file_loc: str,
    username: str, user_id: int, file_name: str
) -> bool:
    return await _common_upload_logic(
        client, message, file_loc, file_name, user_id, username, "subtitle"
    )
