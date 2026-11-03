"""Bot commands for help, status, logs and owner-controlled restart."""
import asyncio
import os
import shutil
import sys
from pathlib import Path

from wzgram import Client, filters
from wzgram.enums import ParseMode
from wzgram.errors import RPCError
from wzgram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from config import Config
from helpers.progress import download_progress, upload_progress
from script import Script
from helpers.logger import logger
from utils.status_utils import get_status_text
from helpers.message_updater import keep_updating_status
from update import UPSTREAM_REPO

DOWNLOADS_DIR = Path("downloads")
RESTART_FILE = Path("restart_msg_id.txt")
_last_status: dict[int, int] = {}


@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message) -> None:
    await message.reply_text(
        text=Script.start_msg(message.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("HELP", callback_data="help_data"),
             InlineKeyboardButton("ABOUT", callback_data="about_data")],
            [InlineKeyboardButton("⭕️Owner⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")],
        ]),
    )


@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message) -> None:
    await message.reply_text(
        text=Script.help_msg(),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("BACK", callback_data="start_data"),
             InlineKeyboardButton("ABOUT", callback_data="about_data")],
            [InlineKeyboardButton("⭕️SUPPORT⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")],
        ]),
    )


@Client.on_message(filters.command("about") & filters.private)
async def about_command(client: Client, message: Message) -> None:
    await message.reply_text(
        text=Script.about_msg(),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("BACK", callback_data="help_data"),
             InlineKeyboardButton("START", callback_data="start_data")],
            [InlineKeyboardButton("SOURCE CODE", url=UPSTREAM_REPO)],
        ]),
    )


@Client.on_message(filters.command("log") & filters.private & filters.user(Config.OWNER_ID))
async def send_log(client: Client, message: Message) -> None:
    log_path = Path("log.txt")
    if not log_path.is_file():
        await message.reply_text("No log file found.")
        return
    try:
        await client.send_document(
            chat_id=message.chat.id, document=str(log_path), caption="Log file"
        )
    except Exception:
        logger.exception("Failed to send bot logs to owner")
        await message.reply_text("Unable to send the log file.")


@Client.on_message(filters.command("restart") & filters.private & filters.user(Config.OWNER_ID))
async def restart_command(client: Client, message: Message) -> None:
    """Finish the update command before replacing this Python process."""
    logger.info("Owner requested a restart")
    reply = await message.reply_text("Restarting the bot...")
    try:
        RESTART_FILE.write_text(str(reply.id), encoding="utf-8")
    except OSError:
        logger.exception("Could not persist restart notification ID")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "update.py",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(
                "Repository update exited %s; restarting installed code. stdout=%s stderr=%s",
                proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
            )
        else:
            logger.info("Repository update finished before restart")
    except Exception:
        logger.exception("Could not execute repository update; restarting installed code")

    # Do not kill every ffmpeg process on the host. Only restart this bot.
    try:
        if DOWNLOADS_DIR.exists():
            shutil.rmtree(DOWNLOADS_DIR)
    except OSError:
        logger.exception("Unable to clear downloads during restart")

    os.execv(sys.executable, [sys.executable, "main.py"])


@Client.on_message(filters.command("status") & filters.private & filters.user(Config.OWNER_ID))
async def status_command(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    old_msg_id = _last_status.get(user_id)
    if old_msg_id:
        try:
            await client.delete_messages(chat_id=message.chat.id, message_ids=old_msg_id)
        except RPCError:
            logger.exception("Could not remove previous status message")

    try:
        report = get_status_text(mount_point=str(Path.cwd()))
        status_msg = await message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        logger.exception("Unable to send bot status report")
        await message.reply_text("Unable to generate status report.")
        return

    _last_status[user_id] = status_msg.id
    if not download_progress and not upload_progress:
        await asyncio.sleep(5)
        try:
            await status_msg.delete()
        except RPCError:
            logger.exception("Could not delete idle status message")
        finally:
            if _last_status.get(user_id) == status_msg.id:
                _last_status.pop(user_id, None)
    else:
        task = keep_updating_status(client, status_msg.chat.id, status_msg.id)
        task.add_done_callback(lambda t: _last_status.pop(user_id, None)
                               if _last_status.get(user_id) == status_msg.id else None)
