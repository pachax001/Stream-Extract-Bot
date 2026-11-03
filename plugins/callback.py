import asyncio
from typing import Any, Dict

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import QueryIdInvalid, RPCError
from config import Config
from script import Script
from helpers.tools import clean_up
from helpers.download import download_file
from helpers.ffmpeg import extract_audio, extract_subtitle
from helpers.logger import logger
from helpers.progress import download_progress, upload_progress, callback_progress
from update import UPSTREAM_REPO


# Helper to safely answer queries
async def answer_query(query: CallbackQuery, text: str = "", show_alert: bool = False) -> bool:
    """Safely answers a callback query, catching QueryIdInvalid."""
    try:
        return await query.answer(text, show_alert=show_alert)
    except QueryIdInvalid:
        logger.warning(f"QueryIdInvalid for query {query.id} - message likely too old or deleted.")
        return False
    except RPCError as e:
        logger.error(f"RPCError answering query {query.id}: {e}")
        return False


@Client.on_callback_query(filters.regex(r"^(start_data|help_data|about_data)$"))
async def handle_navigation_callbacks(client: Client, query: CallbackQuery) -> None:
    """Handles navigation callbacks (start, help, about)."""
    data = query.data
    user_mention = query.from_user.mention if query.from_user else "User"

    mapping = {
        "start_data": (Script.start_msg, [[InlineKeyboardButton("HELP", callback_data="help_data"), InlineKeyboardButton("ABOUT", callback_data="about_data")], [InlineKeyboardButton("⭕️Owner⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")]]) ,
        "help_data": (lambda mention: Script.help_msg(), [[InlineKeyboardButton("BACK", callback_data="start_data"), InlineKeyboardButton("ABOUT", callback_data="about_data")], [InlineKeyboardButton("⭕️SUPPORT⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")]]),
        "about_data": (lambda mention: Script.about_msg(), [[InlineKeyboardButton("BACK", callback_data="help_data"), InlineKeyboardButton("START", callback_data="start_data")], [InlineKeyboardButton("SOURCE CODE", url=UPSTREAM_REPO)]])
    }

    try:
        template_fn, kb = mapping[data]
        text = template_fn(user_mention) # Pass mention to the lambda/function
        await query.message.edit_text(
            text=text,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(kb)
        )
        await answer_query(query)
    except QueryIdInvalid: 
        logger.warning(f"QueryIdInvalid for navigation callback {data}")
    except KeyError:
        logger.error(f"Unknown navigation key in callback: {data}")
        await answer_query(query, "Error: Unknown action.", show_alert=True)
    except Exception as e:
        logger.error(f"Error handling navigation callback `{data}`: {e}")
        await answer_query(query, "An error occurred.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^download_file$"))
async def handle_download_callback(client: Client, query: CallbackQuery) -> None:
    """Handles the 'download_file' callback to start a download."""
    try:
        if query.message and query.message.reply_to_message:
            await query.message.delete()
            asyncio.create_task(download_file(client, query.message.reply_to_message))
            await answer_query(query, "Download started...")
        else:
            logger.warning("Download callback received without a reply_to_message.")
            await answer_query(query, "Error: No message to download.", show_alert=True)
    except Exception as e:
        logger.error(f"Error initiating download via callback: {e}")
        await answer_query(query, "Error starting download.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^progress_msg_"))
async def handle_progress_callback(client: Client, query: CallbackQuery) -> None:
    """Handles progress message callbacks."""
    # The key for callback_progress is callback_key = f"{status_message.chat.id}_{status_message.id}_callback"
    # query.data might be "progress_msg_upload_key" or "progress_msg_download_key"
    # The callback_progress dictionary key is directly constructed from the status message's chat_id and message_id
    
    prog_key_from_cb_data = query.data # e.g. "progress_msg_12345_678_ul" or "progress_msg_12345_678_dl"
                                      # or "progress_msg_12345_678_callback" if old style key was used in button
    
    # The actual key used in callback_progress dictionary is:
    # f"{query.message.chat.id}_{query.message.id}_callback"
    # This is because the button is on the status_message itself.
    actual_cb_prog_key = f"{query.message.chat.id}_{query.message.id}_callback"
    
    entry = callback_progress.get(actual_cb_prog_key)

    if not entry:
        logger.warning(f"No callback_progress entry found for key: {actual_cb_prog_key} (from query data: {prog_key_from_cb_data})")
        await answer_query(query, "Processing... Please wait or data expired.", show_alert=True)
        return

    msg_template = (
        "Progress Details:\n\n"
        "File: {file_name}\n"
        "Type: {ud_type}\n"
        "Completed: {current}\n"
        "Total: {total}\n"
        "Speed: {speed}\n"
        "Progress: {progress:.2f}%\n"
        "Elapsed: {elapsed}\n"
        "ETA: {eta}"
    )
    try:
        progress_text = msg_template.format(**entry)
        await answer_query(query, progress_text, show_alert=True)
    except KeyError as e:
        logger.error(f"KeyError formatting progress message for key {actual_cb_prog_key}: {e}. Entry: {entry}")
        await answer_query(query, "Error retrieving some progress details.", show_alert=True)
    except Exception as e:
        logger.error(f"Error formatting progress message for key {actual_cb_prog_key}: {e}")
        await answer_query(query, "Processing...", show_alert=True)


@Client.on_callback_query(filters.regex(r"^(cancel|close|cancel_)"))
async def handle_cancel_callback(client: Client, query: CallbackQuery) -> None:
    """Handles cancellation callbacks for various stages."""
    data = query.data
    chat_id = query.message.chat.id
    msg_id = query.message.id

    try:
        if data.startswith("cancel_"): # From stream selection prompt
            stream_info_key = data.split("_", 1)[1]
            source_file_path = None
            
            stream_info_dict = download_progress.get(stream_info_key)
            if stream_info_dict and isinstance(stream_info_dict, dict) and stream_info_dict:
                # Get 'file' attribute from the first stream entry's details
                # (assuming all streams in this dict share the same source file)
                first_stream_details = next(iter(stream_info_dict.values()), {})
                source_file_path = first_stream_details.get('file_path') # Changed from 'file' to 'file_path' based on previous refactor
                                                                    # and assuming 'file_path' is the key for the source file location.

            if download_progress.pop(stream_info_key, None):
                logger.info(f"User cancelled stream selection: Removed stream_info_key '{stream_info_key}' from download_progress.")
            
            if source_file_path:
                logger.info(f"User cancelled stream selection: Cleaning up source file '{source_file_path}' for key '{stream_info_key}'.")
                await clean_up(source_file_path)
            else:
                logger.warning(f"User cancelled stream selection for key '{stream_info_key}', but no source_file_path found to clean.")

            await query.message.edit_text("**Selection Cancelled. Associated files and data cleared.**")
            await answer_query(query, "Cancelled.", show_alert=True)

        elif data == "cancel": # From initial download prompt (e.g., choosing what to do with a file)
                               # Or a general cancel button on a progress message
            # Attempt to find any related progress keys. This is broad.
            # The key for download/upload progress is often <chat_id>_<original_msg_id>_<dl/ul>
            # The key for callback_progress is <chat_id>_<status_msg_id>_callback
            
            # If this cancel button is on the status message itself (msg_id):
            status_msg_key_base = f"{chat_id}_{msg_id}"
            callback_key_to_clean = f"{status_msg_key_base}_callback"
            
            cleaned_entries = []
            if callback_progress.pop(callback_key_to_clean, None):
                cleaned_entries.append(f"callback_progress for {callback_key_to_clean}")

            # Try to find related upload/download progress entries.
            # This requires knowledge of how original_message_id is stored or related.
            # Assuming the callback_progress entry (if found) might hold original_msg_id.
            # This part is speculative and might need adjustment based on actual stored data.
            # For now, we only clean callback_progress as it's directly related to the status_msg.
            # More complex cancellations (like stopping an ongoing FFmpeg via SIGTERM) are not handled here.

            if cleaned_entries:
                logger.info(f"General cancel: Cleaned up {', '.join(cleaned_entries)}.")
            else:
                logger.info(f"General cancel for {status_msg_key_base}: No specific progress entries found to clean directly. Downstream processes should handle their own cleanup.")

            await query.message.edit_text("**Cancelled…**")
            await answer_query(query, "Operation Cancelled.", show_alert=True)

        elif data == "close": # Generic close button
            await query.message.edit_text("**Closed.**")
            await answer_query(query, "Closed.", show_alert=False)

    except QueryIdInvalid:
        logger.warning(f"QueryIdInvalid for cancel/close callback (data: {data}) for message {msg_id}")
    except Exception as e:
        logger.error(f"Error in cancel/close callback (data: {data}) for message {msg_id}: {e}", exc_info=True)
        await answer_query(query, "Error during cancellation/closing.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^(audio_|subtitle_)"))
async def handle_extraction_callback(client: Client, query: CallbackQuery) -> None:
    """Handles audio and subtitle extraction callbacks."""
    data = query.data # Format: "audio_<idx_s>_<stream_info_key>" or "subtitle_<idx_s>_<stream_info_key>"
    
    try:
        parts = data.split('_', 2)
        if len(parts) != 3:
            logger.error(f"Invalid extraction callback data format: {data}")
            await query.message.edit_text("**Error: Invalid action format.**")
            await answer_query(query, "Invalid action.", show_alert=True)
            return

        stream_type, idx_s, stream_info_key = parts # stream_info_key is the key for download_progress parent dict
        
        stream_collection = download_progress.get(stream_info_key)
        if not stream_collection or not isinstance(stream_collection, dict):
            logger.warning(f"No download progress stream collection found for key: {stream_info_key} in extraction callback.")
            await query.message.edit_text("**Error: Original download details not found.**\nPerhaps the bot restarted, the process timed out, or was cancelled.")
            await answer_query(query, "Details not found.", show_alert=True)
            return

        entry = stream_collection.get(idx_s) # entry is the specific stream's details
        if not entry or not isinstance(entry, dict):
            logger.warning(f"No stream entry found for index: {idx_s} in stream_info_key: {stream_info_key}")
            await query.message.edit_text(f"**Error: Stream details for index {idx_s} not found.**")
            await answer_query(query, "Stream details not found.", show_alert=True)
            return

        if 'file_path' not in entry: # Ensure 'file_path' (path to the master downloaded file) is in the entry
            logger.error(f"Missing 'file_path' in stream entry for key {stream_info_key}, index {idx_s}. Entry: {entry}")
            await query.message.edit_text("**Error: File path for extraction is missing in stream details.**")
            await answer_query(query, "File path missing.", show_alert=True)
            return
            
        # Add user details to the entry if not already present, for upload function
        if query.from_user:
            entry['user_id'] = query.from_user.id
            entry['user_first_name'] = query.from_user.first_name or "User"
        else: # Should ideally not happen with callbacks from users
            entry['user_id'] = Config.OWNER_ID # Fallback, though not ideal
            entry['user_first_name'] = "BotOwner"

        if stream_type == 'audio':
            await query.message.edit_text("Extracting audio...")
            # Pass stream_info_key to manage cleanup of the parent download_progress entry after extraction
            await extract_audio(client, query.message, entry, stream_info_key) 
        elif stream_type == 'subtitle':
            await query.message.edit_text("Extracting subtitle...")
            await extract_subtitle(client, query.message, entry, stream_info_key)
        else:
            logger.error(f"Unknown stream type in extraction callback: {stream_type}")
            await query.message.edit_text("**Error: Unknown extraction type.**")
        
        # Acknowledgment of the button press is handled by edit_text or within extraction functions.
        # If extraction functions don't call query.answer, an explicit one might be needed here for some cases.
        # However, usually the message is edited, which implicitly answers.

    except QueryIdInvalid:
        logger.warning(f"QueryIdInvalid for extraction callback {data} - message likely already processed or deleted.")
    except ValueError as e: 
        logger.error(f"ValueError in extraction callback `{data}`: {e}", exc_info=True)
        await query.message.edit_text("**Error: Invalid data for extraction.**")
        await answer_query(query, "Invalid data.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in extraction callback `{data}`: {e}", exc_info=True)
        try:
            await query.message.edit_text("**Operation Failed.**")
        except RPCError:
            logger.warning(f"Failed to edit message to 'Operation Failed' for {data} due to RPCError (likely QueryIdInvalid)")
        await answer_query(query, "Operation failed.", show_alert=True)


@Client.on_callback_query() 
async def handle_unknown_callback(client: Client, query: CallbackQuery) -> None:
    """Handles any unknown or unhandled callback queries."""
    logger.info(f"Unhandled callback data: {query.data} from user {query.from_user.id if query.from_user else 'Unknown'}")
    await answer_query(query, "This button seems to be unhandled or outdated.", show_alert=False)
