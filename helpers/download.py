"""Download incoming videos, track progress, and offer their audio/subtitle streams."""
import asyncio
import html
import json
import shutil
import time
from pathlib import Path

from wzgram import Client
from wzgram.enums import ParseMode
from wzgram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from config import Config
from helpers.logger import logger
from helpers.progress import progress_func, download_progress, callback_progress, human_readable_bytes
from helpers.tools import execute, clean_up

MAX_DOWNLOADS_PER_USER = Config.MAX_DOWNLOAD_LIMIT
THRESHOLD_BYTES = Config.THRESHOLD * 1024 ** 3
MOUNT_POINT = Path(Config.MOUNT_POINT)
LOG_CHANNEL = Config.LOG_MEDIA_CHANNEL or Config.LOG_CHANNEL

_LOCK = asyncio.Lock()
_user_download_counts: dict[int, int] = {}
_active_downloads: set[str] = set()


async def download_file(client: Client, message: Message) -> None:
    """Reserve a slot, download the video, and show available streams."""
    user = message.from_user
    if not user or (user.id not in Config.AUTH_USERS and user.id != Config.OWNER_ID):
        return

    media = message.document or message.video
    if not media or not (getattr(media, "mime_type", "") or "").startswith("video/"):
        await message.reply_text("⚠️ Please send a valid video file.")
        return

    user_id = user.id
    unique_key = f"{message.chat.id}_{message.id}_dl"
    download_dir = Path("downloads") / f"{message.chat.id}_{message.id}"
    status_msg = None
    keep_download = False

    # Do not await Telegram calls while holding the lock.
    async with _LOCK:
        if unique_key in _active_downloads:
            rejection = "⚠️ This file is already downloading."
        elif _user_download_counts.get(user_id, 0) >= MAX_DOWNLOADS_PER_USER:
            rejection = f"⚠️ You already have {MAX_DOWNLOADS_PER_USER} active downloads."
        elif len(_active_downloads) >= MAX_DOWNLOADS_PER_USER * 5:
            rejection = "⚠️ Server busy. Please try later."
        else:
            rejection = None
            _active_downloads.add(unique_key)
            _user_download_counts[user_id] = _user_download_counts.get(user_id, 0) + 1

    if rejection:
        await message.reply_text(rejection)
        return

    fname = Path(getattr(media, "file_name", None) or "video").name
    fsize = max(0, getattr(media, "file_size", 0) or 0)
    try:
        free_bytes = shutil.disk_usage(MOUNT_POINT).free
        if free_bytes < THRESHOLD_BYTES + fsize:
            await message.reply_text(
                f"⚠️ Low disk space ({free_bytes / (1024 ** 3):.2f} GB available)."
            )
            return

        status_msg = await client.send_message(
            chat_id=message.chat.id,
            text=f"▶️ Downloading <b>{html.escape(fname)}</b> ({human_readable_bytes(fsize)})...",
            reply_to_message_id=message.id,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Check Progress", callback_data="progress_msg_download")
            ]]),
        )
        progress_key = f"{status_msg.chat.id}_{status_msg.id}_callback"
        callback_progress[progress_key] = {
            "file_name": fname, "ud_type": "dl", "current": "0 B",
            "total": human_readable_bytes(fsize), "speed": "0 B/s",
            "progress": 0.0, "elapsed": "0s", "eta": "calculating",
        }

        path = await _download_with_retries(
            client, message, status_msg, download_dir, fsize, fname
        )
        if path is None:
            await status_msg.edit_text("❌ Failed to download the video after retries.")
            return

        await _forward_to_log(client, message, fname)
        keep_download = await _probe_and_ask_streams(path, fname, status_msg, message)
    except Exception:
        logger.exception("Unexpected download error for chat=%s message=%s", message.chat.id, message.id)
        if status_msg:
            try:
                await status_msg.edit_text("❌ An internal error occurred while processing the video.")
            except Exception:
                logger.exception("Could not update download error status")
        else:
            try:
                await message.reply_text("❌ An internal error occurred.")
            except Exception:
                logger.exception("Could not reply with download error")
    finally:
        if status_msg:
            callback_progress.pop(f"{status_msg.chat.id}_{status_msg.id}_callback", None)
        download_progress.pop(unique_key, None)
        async with _LOCK:
            _active_downloads.discard(unique_key)
            _user_download_counts[user_id] = max(0, _user_download_counts.get(user_id, 1) - 1)
            if not _user_download_counts[user_id]:
                _user_download_counts.pop(user_id, None)
        if not keep_download:
            await clean_up(download_dir)


async def _download_with_retries(
    client: Client,
    message: Message,
    status_msg: Message,
    directory: Path,
    expected_size: int,
    fname: str,
    max_retries: int = 3,
) -> Path | None:
    """Use an isolated directory so failed attempts cannot leave partial files."""
    for attempt in range(1, max_retries + 1):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            result = await client.download_media(
                message,
                file_name=f"{directory}/",
                progress=progress_func,
                progress_args=(
                    "dl", status_msg, time.monotonic(), message, fname, 3.0, {}
                ),
            )
            if result is None:
                raise RuntimeError("Telegram returned no downloaded file")
            path = Path(result)
            if not path.is_file():
                raise OSError(f"Download output does not exist: {path}")
            if expected_size and path.stat().st_size != expected_size:
                raise OSError(
                    f"Download size mismatch: {path.stat().st_size} != {expected_size}"
                )
            return path
        except asyncio.CancelledError:
            await clean_up(directory)
            raise
        except Exception:
            logger.exception("Download attempt %s/%s failed for %s", attempt, max_retries, fname)
            await clean_up(directory)
            if attempt < max_retries:
                await asyncio.sleep(attempt)
    return None


async def _forward_to_log(client: Client, message: Message, fname: str) -> None:
    """Log the original media without preventing extraction on logging failure."""
    if not LOG_CHANNEL:
        return
    user = message.from_user
    uid = user.id
    uname = user.username or user.first_name or "Unknown"
    caption = (
        f"<b>Downloaded:</b> {html.escape(fname)}\n"
        f"<b>By:</b> <a href=\"tg://user?id={uid}\">{html.escape(uname)}</a> ({uid})"
    )
    try:
        await client.copy_message(
            chat_id=int(LOG_CHANNEL),
            from_chat_id=message.chat.id,
            message_id=message.id,
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("Unable to copy downloaded media to log channel %s", LOG_CHANNEL)


async def _probe_and_ask_streams(
    path: Path, fname: str, status_msg: Message, original_msg: Message
) -> bool:
    """Return True only when the file is needed for a displayed stream selection."""
    key = f"{status_msg.chat.id}-{status_msg.id}"
    try:
        out, err, code, _ = await execute(
            ["ffprobe", "-v", "error", "-show_streams", "-print_format", "json", str(path)],
            timeout=120,
        )
        if code != 0:
            raise RuntimeError(f"ffprobe failed: {err}")
        info = json.loads(out)
        buttons = []
        streams = {}
        for stream in info.get("streams", []):
            kind = stream.get("codec_type")
            idx = stream.get("index")
            if kind not in ("audio", "subtitle") or not isinstance(idx, int):
                continue
            language = (stream.get("tags") or {}).get("language", "und")
            streams[str(idx)] = {
                "map": idx,
                "file_path": str(path),
                "file_name": fname,
                "source_file_display_name": fname,
                "original_file_name_for_output": fname,
                "codec_name": stream.get("codec_name") or "",
                "user_id": original_msg.from_user.id,
                "user_first_name": original_msg.from_user.first_name or "User",
            }
            buttons.append([InlineKeyboardButton(
                f"{kind.upper()} {language}",
                callback_data=f"{kind}_{idx}_{key}",
            )])

        if not streams:
            await status_msg.edit_text("❌ No audio or subtitle streams found in this video.")
            return False

        buttons.append([InlineKeyboardButton("CANCEL", callback_data=f"cancel_{key}")])
        download_progress[key] = streams
        await status_msg.edit_text(
            f"🔍 Select stream for <b>{html.escape(fname)}</b>:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception:
        download_progress.pop(key, None)
        logger.exception("Could not probe video streams for %s", path)
        try:
            await status_msg.edit_text("❌ Could not retrieve stream information.")
        except Exception:
            logger.exception("Could not report ffprobe failure")
        return False
