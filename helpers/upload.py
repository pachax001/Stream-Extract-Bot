import asyncio
import time
from pathlib import Path
from typing import Any, Dict

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import Config
from helpers.logger import logger
from helpers.progress import progress_func, upload_progress, callback_progress # download_progress is not directly used here
from helpers.tools import clean_up

# Configuration
LOG_CHANNEL_ID = Config.LOG_CHANNEL # Ensure this is an int or None
BOT_USERNAME = Config.BOT_USERNAME


def _extract_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata (title, artist, duration) from a media file.
    Returns a dictionary with 'title', 'artist', 'duration', and potentially 'thumbnail'.
    """
    data: Dict[str, Any] = {"title": None, "artist": None, "duration": 0, "thumbnail": None}
    try:
        metadata = extractMetadata(createParser(str(file_path)))
        if metadata:
            if metadata.has("title"):
                data["title"] = metadata.get("title")
            if metadata.has("artist"):
                data["artist"] = metadata.get("artist")
            if metadata.has("duration"):
                data["duration"] = metadata.get("duration").seconds
            # Note: hachoir doesn't directly extract thumbnails for most audio formats.
            # This would typically require another library if a specific thumbnail is needed.
            # For now, 'thumbnail' will remain None unless set by other means.
    except Exception as e:
        logger.error(f"Metadata extraction error for {file_path}: {e}")
    return data

def _cleanup_upload(upload_key: str, status_msg_chat_id: int, status_msg_id: int) -> None:
    """
    Remove tracking entries for an upload.
    Args:
        upload_key: The key used for `upload_progress` (e.g., f"{original_msg.chat.id}_{original_msg.id}_ul").
        status_msg_chat_id: Chat ID of the status message.
        status_msg_id: Message ID of the status message.
    """
    if upload_progress.pop(upload_key, None):
        logger.debug(f"Cleaned up upload_progress for key: {upload_key}")
    
    callback_key = f"{status_msg_chat_id}_{status_msg_id}_callback"
    if callback_progress.pop(callback_key, None):
        logger.debug(f"Cleaned up callback_progress for key: {callback_key}")

async def _common_upload_logic(
    client: Client,
    original_message: Message, # This is the message from the callback query in extraction context
    file_loc: str,
    file_name_display: str, # The actual name of the file being uploaded
    user_id: int, # User who initiated
    username: str, # Username of initiator
    upload_type: str, # "audio" or "subtitle"
) -> None:
    """
    Common logic for uploading audio or subtitle files.
    `original_message` here refers to the message associated with the callback query that initiated the upload.
    """
    file_path = Path(file_loc)
    if not file_path.exists():
        logger.error(f"Upload error: File {file_loc} not found for {original_message.id}.")
        await original_message.edit_text(f"**Error: Output file for {file_name_display} not found.**")
        return

    # Key for upload_progress, based on the message that triggered the extraction/upload flow
    upload_key = f"{original_message.chat.id}_{original_message.id}_ul"
    
    # Initialize a dictionary for managing last_update_time for this specific upload task's progress_func calls
    task_last_update_time = {}

    start_time = time.monotonic()
    
    # Initial record for upload_progress (optional, as progress_func will create/update it)
    # upload_progress[upload_key] = {
    #     "file_name": file_name_display,
    #     "start_time": start_time,
    #     "user_id": user_id,
    #     "status": "starting"
    # }

    status_msg_text = f"**Uploading {upload_type}**: `{file_name_display}`"
    status_msg = await original_message.edit_text(
        text=status_msg_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text="Progress", callback_data=f"progress_msg_{upload_key}")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

    meta = _extract_metadata(file_path) if upload_type == "audio" else {}
    log_caption = f"Extracted by: <a href='tg://user?id={user_id}'>{username}</a>\nFile: {file_name_display}"

    try:
        progress_args_tuple = (
            "ul",                   # ud_type
            status_msg,             # status_message (the message we update with progress)
            start_time,
            original_message,       # original_message (message that initiated the command)
            file_name_display,      # file_name_display
            3.0,                    # interval
            task_last_update_time   # last_update_time dict for this task
        )

        if upload_type == "audio":
            sent_message = await client.send_audio(
                chat_id=original_message.chat.id,
                audio=file_loc,
                thumb=meta.get("thumbnail"), # Pyrogram expects a file path or TG file_id
                caption=f"Uploaded by @{BOT_USERNAME}\nFile: {file_name_display}",
                title=meta.get("title") or file_name_display,
                performer=meta.get("artist"),
                duration=meta.get("duration"),
                progress=progress_func,
                progress_args=progress_args_tuple
            )
            if LOG_CHANNEL_ID:
                await client.send_audio(
                    chat_id=LOG_CHANNEL_ID, audio=file_loc, thumb=meta.get("thumbnail"), caption=log_caption,
                    title=meta.get("title") or file_name_display, performer=meta.get("artist"),
                    duration=meta.get("duration"), parse_mode=ParseMode.HTML
                )
        elif upload_type == "subtitle":
            sent_message = await client.send_document(
                chat_id=original_message.chat.id,
                document=file_loc,
                caption=f"Uploaded by @{BOT_USERNAME}\nFile: {file_name_display}",
                progress=progress_func,
                progress_args=progress_args_tuple
            )
            if LOG_CHANNEL_ID:
                await client.send_document(
                    chat_id=LOG_CHANNEL_ID, document=file_loc, caption=log_caption, parse_mode=ParseMode.HTML
                )
        else:
            logger.error(f"Unknown upload type: {upload_type}")
            await status_msg.edit_text("**Error: Unknown upload type.**")
            return # No cleanup here as it's a programming error

        await status_msg.delete() # Delete the "Uploading..." message
        logger.info(f"Successfully uploaded and logged {file_name_display} (Key: {upload_key})")

    except Exception as e:
        logger.error(f"Upload error for {file_name_display} (Key: {upload_key}): {e}", exc_info=True)
        error_text = f"**Error uploading {file_name_display}.**"
        try:
            await status_msg.edit_text(text=error_text)
        except Exception as e_edit:
            logger.error(f"Failed to edit status message on upload error: {e_edit}")
        # No return here, cleanup will happen in finally
    finally:
        await clean_up(file_loc) # Delete the local file
        _cleanup_upload(upload_key, status_msg.chat.id, status_msg.id)
        logger.debug(f"Finished cleanup for {upload_key}")


async def upload_audio(
    client: Client,
    message: Message, # Message from the callback query (e.g., after user clicks "extract audio")
    file_loc: str,    # Path to the audio file to be uploaded
    username: str,    # Username of the user who initiated
    user_id: int,     # User ID of the user who initiated
    file_name: str    # Name of the audio file
) -> None:
    """
    Upload an audio stream to the user and log channel with progress.
    `message` is the callback query's message.
    """
    await _common_upload_logic(
        client=client,
        original_message=message, # This is the callback query's message
        file_loc=file_loc,
        file_name_display=file_name,
        user_id=user_id,
        username=username,
        upload_type="audio"
    )

async def upload_subtitle(
    client: Client,
    message: Message, # Message from the callback query
    file_loc: str,
    username: str,
    user_id: int,
    file_name: str
) -> None:
    """
    Upload a subtitle file to the user and log channel with progress.
    `message` is the callback query's message.
    """
    await _common_upload_logic(
        client=client,
        original_message=message, # This is the callback query's message
        file_loc=file_loc,
        file_name_display=file_name,
        user_id=user_id,
        username=username,
        upload_type="subtitle"
    )
