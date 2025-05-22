import os
import sys
import shutil
import asyncio
from pathlib import Path
from subprocess import CalledProcessError

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from config import Config
from script import Script
from helpers.logger import logger
from utils.status_utils import get_status_text
from helpers.message_updater import keep_updating_status
from helpers.tools import clean_up

# Paths
DOWNLOADS_DIR = Path("downloads")
RESTART_FILE = Path("restart_msg_id.txt")


@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message) -> None:
    """
    Handle /start command: send welcome message with keyboard.
    """
    await message.reply_text(
        text=Script.start_msg(message.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("HELP", callback_data="help_data"),
                InlineKeyboardButton("ABOUT", callback_data="about_data"),
            ],
            [InlineKeyboardButton("⭕️Owner⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")]
        ])
    )


@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message) -> None:
    """
    Handle /help command: send usage instructions.
    """
    await message.reply_text(
        text=Script.help_msg(),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("BACK", callback_data="start_data"),
                InlineKeyboardButton("ABOUT", callback_data="about_data"),
            ],
            [InlineKeyboardButton("⭕️SUPPORT⭕️", url=f"https://t.me/{Config.BOT_USERNAME}")]
        ])
    )


@Client.on_message(filters.command("about") & filters.private)
async def about_command(client: Client, message: Message) -> None:
    """
    Handle /about command: send bot details.
    """
    await message.reply_text(
        text=Script.about_msg(),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("BACK", callback_data="help_data"),
                InlineKeyboardButton("START", callback_data="start_data"),
            ],
            [
                InlineKeyboardButton(
                    "SOURCE CODE",
                    url=Config.UPSTREAM_REPO if hasattr(Config, 'UPSTREAM_REPO') else "https://github.com/pachax001/Stream-Extract-Bot"
                )
            ]
        ])
    )


@Client.on_message(filters.command("log") & filters.private & filters.user(Config.OWNER_ID))
async def send_log(client: Client, message: Message) -> None:
    """
    Handle /log command: send the log.txt file to owner.
    """
    log_path = Path("log.txt")
    if log_path.exists():
        await client.send_document(
            chat_id=message.chat.id,
            document=str(log_path),
            caption="Log file"
        )
    else:
        await message.reply_text("No log file found.")


async def _is_ffmpeg_running() -> bool:
    """
    Check if any ffmpeg process is active on the system.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "pgrep", "-f", "ffmpeg",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        out, _ = await proc.communicate()
        return bool(out.strip())
    except CalledProcessError:
        return False


@Client.on_message(filters.command("restart") & filters.private & filters.user(Config.OWNER_ID))
async def restart_command(client: Client, message: Message) -> None:
    """
    Handle /restart: cleanup, update code, and restart the bot.
    """
    logger.info("Restarting the bot...")
    resp = await message.reply_text("Restarting the bot...")

    # Save message ID for post-restart edit
    RESTART_FILE.write_text(str(resp.id))

    # Cleanup downloads directory
    if DOWNLOADS_DIR.exists():
        shutil.rmtree(DOWNLOADS_DIR, ignore_errors=True)

    # Terminate ffmpeg if running
    if await _is_ffmpeg_running():
        await asyncio.create_subprocess_exec("pkill", "-9", "-f", "ffmpeg")

    # Run update script
    await asyncio.create_subprocess_exec("python3", "update.py")

    # Restart process
    os.execl(sys.executable, sys.executable, "main.py")


@Client.on_message(filters.command("status") & filters.private & filters.user(Config.OWNER_ID))
async def status_command(client: Client, message: Message) -> None:
    """
    Handle /status: send a status report and update it periodically.
    """
    report = get_status_text(mount_point=str(Path.cwd()))
    status_msg = await message.reply_text(
        report,
        parse_mode=ParseMode.MARKDOWN
    )
    keep_updating_status(client, status_msg.chat.id, status_msg.id)
