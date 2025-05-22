import asyncio
import time
from pathlib import Path
from typing import Any, Dict

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from helpers.logger import logger
from helpers.progress import progress_func, upload_progress, callback_progress
from helpers.tools import clean_up

# Configuration
LOG_CHANNEL = Config.LOG_CHANNEL
BOT_USERNAME = Config.BOT_USERNAME


def _extract_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata (title, artist, duration) from a media file.
    """
    metadata = extractMetadata(createParser(str(file_path)))
    data: Dict[str, Any] = {"title": None, "artist": None, "duration": 0}
    if metadata:
        if metadata.has("title"):
            data["title"] = metadata.get("title")
        if metadata.has("artist"):
            data["artist"] = metadata.get("artist")
        if metadata.has("duration"):
            data["duration"] = metadata.get("duration").seconds
    return data


async def upload_audio(
    client: Client,
    message: Message,
    file_loc: str,
    username: str,
    user_id: int,
    file_name: str
) -> None:
    """
    Upload an audio stream to the user and log channel with progress.
    """
    unique_id = f"{message.chat.id}_{message.id}_upload"
    start_time = time.monotonic()
    upload_progress[unique_id] = {"file_name": file_name, "start_time": start_time, "user_id": user_id}

    # Show initial uploading message
    status_msg = await message.edit_text(
        text="**Uploading extracted stream...**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text="Progress", callback_data="progress_msg_upload")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

    # Extract metadata
    file_path = Path(file_loc)
    meta = _extract_metadata(file_path)

    try:
        await asyncio.sleep(1)
        logger.info(f"Starting upload for {file_name}")

        await client.send_audio(
            chat_id=message.chat.id,
            audio=file_loc,
            thumb=meta.get("thumbnail"),
            caption=f"Uploaded by {BOT_USERNAME}",
            title=meta.get("title"),
            performer=meta.get("artist"),
            duration=meta.get("duration"),
            progress=progress_func,
            progress_args=("upload", status_msg, start_time, message)
        )
    except Exception as e:
        logger.error(f"upload_audio error for {file_name}: {e}")
        await status_msg.edit_text(
            text=f"**Error uploading {file_name}.** Check logs."
        )
        await clean_up(file_loc)
        _cleanup_upload(unique_id)
        return

    # Forward to log channel if configured
    if LOG_CHANNEL:
        try:
            await asyncio.sleep(1)
            logger.info(f"Logging upload for {file_name}")
            await client.send_audio(
                chat_id=int(LOG_CHANNEL),
                audio=file_loc,
                thumb=meta.get("thumbnail"),
                caption=f"Extracted by: <a href='tg://user?id={user_id}'>{username}</a>",
                title=meta.get("title"),
                performer=meta.get("artist"),
                duration=meta.get("duration"),
                parse_mode=ParseMode.HTML,
                progress=progress_func,
                progress_args=("upload", status_msg, start_time, message)
            )
        except Exception as e:
            logger.error(f"Error logging upload for {file_name}: {e}")
            await status_msg.edit_text(
                text=f"**Error sending {file_name} to log channel.**"
            )
            await clean_up(file_loc)
            _cleanup_upload(unique_id)
            return

    # Cleanup resources
    await status_msg.delete()
    await clean_up(file_loc)
    _cleanup_upload(unique_id)


async def upload_subtitle(
    client: Client,
    message: Message,
    file_loc: str,
    username: str,
    user_id: int,
    file_name: str
) -> None:
    """
    Upload a subtitle file to the user and log channel with progress.
    """
    unique_id = f"{message.chat.id}_{message.id}_upload"
    start_time = time.monotonic()
    upload_progress[unique_id] = {"file_name": file_name, "start_time": start_time, "user_id": user_id}

    status_msg = await message.edit_text(
        text="**Uploading extracted subtitle...**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text="Progress", callback_data="progress_msg_upload")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        await asyncio.sleep(1)
        logger.info(f"Starting subtitle upload for {file_name}")

        await client.send_document(
            chat_id=message.chat.id,
            document=file_loc,
            caption=f"Uploaded by {BOT_USERNAME}",
            progress=progress_func,
            progress_args=("upload", status_msg, start_time, message)
        )
    except Exception as e:
        logger.error(f"upload_subtitle error for {file_name}: {e}")
        await status_msg.edit_text(
            text=f"**Error uploading subtitle {file_name}.** Check logs."
        )
        await clean_up(file_loc)
        _cleanup_upload(unique_id)
        return

    # Forward to log channel if configured
    if LOG_CHANNEL:
        try:
            await asyncio.sleep(1)
            logger.info(f"Logging subtitle for {file_name}")
            await client.send_document(
                chat_id=int(LOG_CHANNEL),
                document=file_loc,
                caption=f"Extracted by: <a href='tg://user?id={user_id}'>{username}</a>",
                parse_mode=ParseMode.HTML,
                progress=progress_func,
                progress_args=("upload", status_msg, start_time, message)
            )
        except Exception as e:
            logger.error(f"Error logging subtitle {file_name}: {e}")
            await status_msg.edit_text(
                text=f"**Error sending subtitle to log channel.**"
            )
            await clean_up(file_loc)
            _cleanup_upload(unique_id)
            return

    # Cleanup resources
    await status_msg.delete()
    await clean_up(file_loc)
    _cleanup_upload(unique_id)


def _cleanup_upload(unique_id: str) -> None:
    """
    Remove tracking entries for an upload.
    """
    upload_progress.pop(unique_id, None)
    callback_progress.pop(f"{unique_id}_callback", None)
