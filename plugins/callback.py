"""Inline button handlers for navigation, downloads and stream extraction."""
import asyncio
from pathlib import Path

from wzgram import Client, filters
from wzgram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from wzgram.errors import QueryIdInvalid, RPCError

from config import Config
from script import Script
from helpers.tools import clean_up
from helpers.download import download_file
from helpers.ffmpeg import extract_audio, extract_subtitle
from helpers.logger import logger
from helpers.progress import stream_selections, callback_progress
from update import UPSTREAM_REPO

_active_extractions: set[str] = set()


async def answer_query(query: CallbackQuery, text: str = "", show_alert: bool = False) -> None:
    try:
        await query.answer(text[:200], show_alert=show_alert)
    except QueryIdInvalid:
        logger.debug("Expired callback query %s", query.id)
    except RPCError:
        logger.exception("Telegram rejected callback query %s", query.id)


async def _safe_edit(query: CallbackQuery, text: str) -> None:
    if not query.message:
        return
    try:
        await query.message.edit_text(text)
    except RPCError:
        logger.exception("Failed to edit callback message id=%s", query.message.id)


async def _check_access(query: CallbackQuery, owner_id: int | None = None) -> bool:
    user_id = query.from_user.id if query.from_user else None
    if user_id is None or (user_id not in Config.AUTH_USERS and user_id != Config.OWNER_ID):
        await answer_query(query, "You are not authorized to use this bot.", True)
        return False
    if owner_id is not None and user_id != owner_id:
        await answer_query(query, "This action belongs to another user.", True)
        return False
    return True


@Client.on_callback_query(filters.regex(r"^(start_data|help_data|about_data)$"))
async def handle_navigation_callbacks(client: Client, query: CallbackQuery) -> None:
    if not query.message:
        await answer_query(query, "Message no longer available.", True)
        return
    mention = query.from_user.mention if query.from_user else "User"
    mapping = {
        "start_data": (
            Script.start_msg(mention),
            [[InlineKeyboardButton("HELP", callback_data="help_data"),
              InlineKeyboardButton("ABOUT", callback_data="about_data")],
             [InlineKeyboardButton("⭕️Owner⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")]],
        ),
        "help_data": (
            Script.help_msg(),
            [[InlineKeyboardButton("BACK", callback_data="start_data"),
              InlineKeyboardButton("ABOUT", callback_data="about_data")],
             [InlineKeyboardButton("⭕️SUPPORT⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")]],
        ),
        "about_data": (
            Script.about_msg(),
            [[InlineKeyboardButton("BACK", callback_data="help_data"),
              InlineKeyboardButton("START", callback_data="start_data")],
             [InlineKeyboardButton("SOURCE CODE", url=UPSTREAM_REPO)]],
        ),
    }
    try:
        text, buttons = mapping[query.data]
        await query.message.edit_text(
            text, disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except RPCError:
        logger.exception("Navigation callback failed: %s", query.data)
    except KeyError:
        logger.warning("Unknown navigation callback: %s", query.data)
    finally:
        await answer_query(query)


@Client.on_callback_query(filters.regex(r"^download_file$"))
async def handle_download_callback(client: Client, query: CallbackQuery) -> None:
    if not await _check_access(query):
        return
    if not query.message or not query.message.reply_to_message:
        await answer_query(query, "Original video is no longer available.", True)
        return
    original = query.message.reply_to_message
    if not original.from_user or original.from_user.id != query.from_user.id:
        await answer_query(query, "This video belongs to another user.", True)
        return
    await answer_query(query, "Download started.")
    try:
        await query.message.delete()
    except RPCError:
        logger.exception("Could not delete download confirmation message")
    task = asyncio.create_task(download_file(client, original))
    task.add_done_callback(_log_background_failure)


def _log_background_failure(task: asyncio.Task) -> None:
    if not task.cancelled():
        try:
            task.result()
        except Exception:
            logger.exception("Download task failed unexpectedly")


@Client.on_callback_query(filters.regex(r"^progress_msg_"))
async def handle_progress_callback(client: Client, query: CallbackQuery) -> None:
    if not await _check_access(query):
        return
    if not query.message:
        await answer_query(query, "Progress message not available.", True)
        return
    key = f"{query.message.chat.id}_{query.message.id}_callback"
    entry = callback_progress.get(key)
    if not entry:
        await answer_query(query, "Processing or progress details expired.", True)
        return
    try:
        details = (
            f"Progress Details:\n\nFile: {entry['file_name']}\n"
            f"Type: {entry['ud_type']}\nCompleted: {entry['current']}\n"
            f"Total: {entry['total']}\nSpeed: {entry['speed']}\n"
            f"Progress: {entry['progress']:.2f}%\n"
            f"Elapsed: {entry['elapsed']}\nETA: {entry['eta']}"
        )
        await answer_query(query, details, True)
    except (KeyError, TypeError, ValueError):
        logger.exception("Invalid progress data for %s", key)
        await answer_query(query, "Progress temporarily unavailable.", True)


@Client.on_callback_query(filters.regex(r"^(cancel|close|cancel_)"))
async def handle_cancel_callback(client: Client, query: CallbackQuery) -> None:
    if not await _check_access(query):
        return
    if not query.message:
        await answer_query(query, "Message no longer available.", True)
        return
    data = query.data
    try:
        if data.startswith("cancel_"):
            key = data.removeprefix("cancel_")
            expected = f"{query.message.chat.id}-{query.message.id}"
            if key != expected:
                await answer_query(query, "This selection has expired.", True)
                return
            if key in _active_extractions:
                await answer_query(query, "Extraction is already in progress.", True)
                return
            streams = stream_selections.get(key)
            if not streams:
                await answer_query(query, "Selection already cleared.", True)
                return
            owner = next(iter(streams.values())).get("user_id")
            if not await _check_access(query, owner):
                return
            stream_selections.pop(key, None)
            source = next(iter(streams.values())).get("file_path")
            if source:
                await clean_up(source)
                path = Path(source)
                if path.parent.parent == (Path.cwd() / "downloads"):
                    await clean_up(path.parent)
            await _safe_edit(query, "Selection cancelled. Associated files cleared.")
        elif data == "cancel":
            callback_progress.pop(
                f"{query.message.chat.id}_{query.message.id}_callback", None
            )
            await _safe_edit(query, "Cancelled.")
        else:
            await _safe_edit(query, "Closed.")
        await answer_query(query)
    except Exception:
        logger.exception("Failed to handle cancel callback %s", data)
        await answer_query(query, "Unable to cancel this operation.", True)


@Client.on_callback_query(filters.regex(r"^(audio_|subtitle_)"))
async def handle_extraction_callback(client: Client, query: CallbackQuery) -> None:
    if not await _check_access(query):
        return
    if not query.message:
        await answer_query(query, "Selection message no longer available.", True)
        return
    data = query.data
    parts = data.split("_", 2)
    if len(parts) != 3:
        await answer_query(query, "Invalid extraction action.", True)
        return
    kind, index, key = parts
    expected = f"{query.message.chat.id}-{query.message.id}"
    if key != expected:
        await answer_query(query, "This selection has expired.", True)
        return
    streams = stream_selections.get(key)
    entry = streams.get(index) if isinstance(streams, dict) else None
    if not isinstance(entry, dict):
        await answer_query(query, "Stream selection expired or was cancelled.", True)
        return
    if not await _check_access(query, entry.get("user_id")):
        return
    if entry.get("stream_type") != kind or not entry.get("file_path"):
        await answer_query(query, "Invalid stream selection.", True)
        return
    if key in _active_extractions:
        await answer_query(query, "Extraction is already in progress.", True)
        return

    _active_extractions.add(key)
    await answer_query(query, "Extracting...")
    try:
        if kind == "audio":
            await extract_audio(client, query.message, entry, key)
        else:
            await extract_subtitle(client, query.message, entry, key)
    except Exception:
        logger.exception("Unhandled extraction callback failure: %s", data)
        await _safe_edit(query, "❌ Operation failed.")
    finally:
        _active_extractions.discard(key)


@Client.on_callback_query()
async def handle_unknown_callback(client: Client, query: CallbackQuery) -> None:
    logger.info("Unhandled callback: %r", query.data)
    await answer_query(query, "This button is outdated.", False)
