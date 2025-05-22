import asyncio
from typing import Any, Dict

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import QueryIdInvalid
from config import Config
from script import Script
from helpers.tools import clean_up
from helpers.download import download_file, _user_download_counts, _active_downloads
from helpers.ffmpeg import extract_audio, extract_subtitle
from helpers.logger import logger
from helpers.progress import download_progress, upload_progress, callback_progress
from update import UPSTREAM_REPO


@Client.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery) -> None:
    """
    Central handler for all callback queries (button presses).
    Handles navigation (start/help/about), download initiation, progress alerts,
    extraction commands, and cancellation.
    """
    data = query.data or ""
    chat_id = query.message.chat.id
    msg_id = query.message.id
    #await query.answer()

    # ------- NAVIGATION BUTTONS -------
    if data in ("start_data", "help_data", "about_data"):
        mapping = {
            "start_data": (Script.start_msg, [[InlineKeyboardButton("HELP", callback_data="help_data"), InlineKeyboardButton("ABOUT", callback_data="about_data")], [InlineKeyboardButton("⭕️Owner⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")]]),
            "help_data": (lambda _: Script.help_msg(), [[InlineKeyboardButton("BACK", callback_data="start_data"), InlineKeyboardButton("ABOUT", callback_data="about_data")], [InlineKeyboardButton("⭕️SUPPORT⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")]]),
            "about_data": (lambda _: Script.about_msg(), [[InlineKeyboardButton("BACK", callback_data="help_data"), InlineKeyboardButton("START", callback_data="start_data")], [InlineKeyboardButton("SOURCE CODE", url=UPSTREAM_REPO)]])
        }
        try:
            template_fn, kb = mapping[data]
            text = template_fn(query.from_user.mention)
            await query.message.edit_text(
                text=text,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except QueryIdInvalid:
            logger.warning("CallbackQuery invalid during navigation")
        except Exception as e:
            logger.error(f"Error handling `{data}` navigation: {e}")
        return

    # ------- DOWNLOAD BUTTON -------
    if data == "download_file":
        # Delete prompt and start download in background
        try:
            await query.message.delete()
            asyncio.create_task(download_file(client, query.message.reply_to_message))
        except Exception as e:
            logger.error(f"Error initiating download: {e}")
        return

    # ------- PROGRESS ALERTS -------
    if data.startswith("progress_msg_"):
        prog_key = f"{chat_id}_{msg_id}_callback"
        registry = callback_progress
        entry = registry.get(prog_key)
        if not entry:
            return await query.answer("Processing...", show_alert=True)

        msg = (
            "Progress Details...\n\n"
            "Completed: {current}\n"
            "Total: {total}\n"
            "Speed: {speed}\n"
            "Progress: {progress:.2f}%\n"
            "Elapsed: {elapsed}\n"
            "ETA: {eta}"
        )
        try:
            return await query.answer(msg.format(**entry), show_alert=True)
        except Exception:
            await query.answer("Processing...", show_alert=True)
        return

    # ------- CANCEL BUTTON -------
    if data in ("cancel", "close"):  # support both keys
        try:
            key_parts = data.split("_")
            # cleanup entries if present
            for registry in (download_progress, upload_progress, callback_progress):
                registry.pop(f"{chat_id}_{msg_id}", None)
            await query.message.edit_text("**Cancelled…**")
            await query.answer("Cancelled.", show_alert=True)
        except Exception as e:
            logger.error(f"Error cancelling operation: {e}")
        return

    # ------- STREAM EXTRACTION -------
    if data.startswith(('audio_', 'subtitle_')):
        try:
            stream_type, idx_s, key = data.split('_', 2)
            #idx = int(idx_s)
            bucket = download_progress.get(key,{})

            # key was message_chat-message_id
            #entry: Dict[str, Any] = download_progress.get(key) or {}
            entry = bucket.get(idx_s)
            if not entry:
                await query.message.edit_text("**Details Not Found**")
                return
            if stream_type == 'audio':
                await extract_audio(client, query.message, entry)
            else:
                await extract_subtitle(client, query.message, entry)
        except QueryIdInvalid:
            logger.warning("CallbackQuery invalid during extraction")
        except Exception as e:
            await query.message.edit_text("**Operation Failed**")
            logger.error(f"Error in extraction callback `{data}`: {e}")
        return

    # Unhandled callback
    logger.info(f"Unhandled callback data: {data}")
    await query.answer()
