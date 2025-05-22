import asyncio
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from config import Config
from helpers.logger import logger
from helpers.progress import progress_func, download_progress, callback_progress
from helpers.tools import execute, clean_up

# --- Configuration & Shared State ---
MAX_DOWNLOADS_PER_USER = Config.MAX_DOWNLOAD_LIMIT
THRESHOLD_BYTES = Config.THRESHOLD * 1024 ** 3
MOUNT_POINT = Path(Config.MOUNT_POINT)
LOG_CHANNEL = Config.LOG_MEDIA_CHANNEL or Config.LOG_CHANNEL

_LOCK = asyncio.Lock()
_user_download_counts: Dict[int, int] = {}
_active_downloads: Dict[str, Any] = {}


async def download_file(client: Client, message: Message) -> None:
    """
    Handle a user's download request:
      1. Enforce per-user and global download limits
      2. Validate media and disk space
      3. Download with retries and progress tracking
      4. Forward to log channel
      5. Probe streams and prompt user for extraction
    """
    user_id = message.from_user.id
    op_msg: Optional[Message] = None
    download_path: Optional[Path] = None
    unique_key = f"{message.chat.id}_{message.id}_dl"

    # Reserve a download slot
    async with _LOCK:
        _user_download_counts.setdefault(user_id, 0)
        if _user_download_counts[user_id] >= MAX_DOWNLOADS_PER_USER:
            await message.reply_text(f"⚠️ You already have {MAX_DOWNLOADS_PER_USER} active downloads.")
            return
        if len(_active_downloads) >= int(MAX_DOWNLOADS_PER_USER)*5:
            await message.reply_text(f"⚠️ Server busy with {len(_active_downloads)} downloads. Please try later.")
            return
        _user_download_counts[user_id] += 1
        _active_downloads[unique_key] = {}

    try:
        # Validate replied media
        media = message
        if not media or not (media.document or media.video):
            await message.reply_text("⚠️ Please reply to a valid media file.")
            return

        doc = media.document or media.video
        fname = getattr(doc, "file_name", "unknown")
        fsize = getattr(doc, "file_size", 0)
        nice_size = f"{fsize / (1024**2):.2f} MB" if fsize else "Unknown size"

        # Disk space check
        free_bytes = shutil.disk_usage(MOUNT_POINT)[2]
        if free_bytes < THRESHOLD_BYTES:
            await message.reply_text(f"⚠️ Low disk space ({free_bytes / (1024**3):.2f} GB available).")
            return

        # Initial status message with progress button
        op_msg = await client.send_message(
            chat_id=message.chat.id,
            text=f"▶️ Downloading **{fname}** ({nice_size})...",
            reply_to_message_id=media.id,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Check Progress", callback_data="progress_msg_download")]]
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        # mark callback tracking
        key = f"{op_msg.chat.id}_{op_msg.id}_callback"
        callback_progress[key] = {
            "file_name": fname,
            "current": "0 B",
            "total": nice_size,
            "speed": "0 B/s",
            "progress": 0.0,
            "elapsed": "0ms",
            "eta": "calculating"
        }

        # Download media with retry logic
        download_path = await _download_with_retries(
            client, media, op_msg, original_size=fsize
        )
        if not download_path:
            await op_msg.edit_text(f"❌ Failed to download **{fname}** after retries.")
            return

        # Forward to logging channel
        await _forward_to_log(client, media, fname)

        # Probe streams and prompt user
        await _probe_and_ask_streams(client, download_path, fname, op_msg, message)

    except Exception:
        logger.exception("download_file: unexpected error")
        if message:
            await message.reply_text("❌ An internal error occurred.")
    finally:
        # Cleanup progress tracking
        if op_msg:
            callback_progress.pop(f"{op_msg.chat.id}_{op_msg.id}_callback", None)
        # Release slot
        async with _LOCK:
            _user_download_counts[user_id] = max(0, _user_download_counts.get(user_id, 1) - 1)
            _active_downloads.pop(unique_key, None)
            download_progress.pop(unique_key, None)


async def _download_with_retries(
    client: Client,
    media: Message,
    status_msg: Message,
    original_size: int,
    max_retries: int = 3
) -> Optional[Path]:
    """
    Attempt to download media up to max_retries, cleaning incomplete files on failure.
    """
    for attempt in range(1, max_retries + 1):
        path: Optional[Path] = None
        try:
            path_str = await client.download_media(
                media,
                progress=progress_func,
                progress_args=("dl", status_msg, asyncio.get_event_loop().time(), media),
            )
            if not path_str:
                raise RuntimeError("No file path returned by download_media.")

            path = Path(path_str)
            if path.stat().st_size != original_size:
                logger.warning(
                    f"Attempt {attempt}: size mismatch {path.stat().st_size} != {original_size}, retrying"
                )
                await clean_up(path)
                continue

            await status_msg.edit_text(f"✅ Downloaded in {attempt} attempt(s).")
            return path

        except MessageNotModified:
            continue
        except Exception as e:
            logger.error(f"Attempt {attempt} download error: {e}")
            if path:
                await clean_up(path)
    return None


async def _forward_to_log(
    client: Client,
    media: Message,
    fname: str
) -> None:
    """
    Copy the downloaded media to the log channel, annotating it
    with the downloader’s username, user ID, and profile link.
    """
    if not LOG_CHANNEL:
        return

    # Extract user info
    user = media.from_user
    uid = user.id
    # Fallback to first name if no username
    uname = user.username or user.first_name or "Unknown"
    # Telegram profile link
    profile_link = f"tg://user?id={uid}"

    # Build rich caption
    caption = (
        f"<b>Downloaded:</b> {fname}\n"
        f"<b>By:</b> <a href=\"{profile_link}\">{uname}</a> (`{uid}`)"
    )

    try:
        await asyncio.sleep(0.3)
        await client.copy_message(
            chat_id=int(LOG_CHANNEL),
            from_chat_id=media.chat.id,
            message_id=media.id,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    except UsernameNotOccupied:
        logger.info("Log channel invalid; skipping log copy.")
    except Exception as e:
        logger.error(f"_forward_to_log failed: {e}")



async def _probe_and_ask_streams(
    client: Client,
    path: Path,
    fname: str,
    status_msg: Message,
    original_msg: Message,
) -> None:
    """
    Run ffprobe to list audio/subtitle streams and prompt user to select one.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_streams",
            "-print_format", "json",
            str(path)
        ]
        out, err, code, _ = await execute(cmd)
        if code != 0:
            raise RuntimeError(err)

        info = json.loads(out)
        buttons = []
        key = f"{status_msg.chat.id}-{status_msg.id}"
        download_progress[key] = {}
        for stream in info.get("streams", []):
            t = stream.get("codec_type")
            if t in {"audio", "subtitle"}:
                idx = stream["index"]
                lang = stream.get("tags", {}).get("language", "und")
                name = stream.get("codec_name", t)  # e.g. "aac", "mp3", "subrip"
                cb = f"{t}_{idx}_{key}"
                download_progress[key][str(idx)] = {"map": idx, "file": str(path), "location": str(path), "file_name": fname,
                                          "user_id": original_msg.from_user.id,
                                          "user_first_name": original_msg.from_user.first_name or "<unknown>",
                                          "name": name, }
                buttons.append([
                    InlineKeyboardButton(f"{t.upper()} {lang}", callback_data=cb)
                ])


        buttons.append([InlineKeyboardButton("CANCEL", f"cancel_{key}")])
        await status_msg.edit_text(
            f"🔍 Select stream for **{fname}**:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"_probe_and_ask_streams error: {e}")
        await status_msg.edit_text("❌ Could not retrieve stream information.")
