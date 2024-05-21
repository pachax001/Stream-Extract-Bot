#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @hellohoneybuny


from pyrogram import filters
from pyrogram import Client as trojanz
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from script import Script
import os
import sys
import subprocess
from helpers.logger import logger
import asyncio
@trojanz.on_message(filters.command(["start"]) & filters.private)
async def start(client, message):
    await message.reply_text(
        text=Script.START_MSG.format(message.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("HELP", callback_data="help_data"),
                    InlineKeyboardButton("ABOUT", callback_data="about_data"),
                ],
                [
                    InlineKeyboardButton(
                        "⭕️Owner⭕️", url="https://t.me/gunaya001")
                ]
            ]
        ),
        reply_to_message_id=message.id
    )


@trojanz.on_message(filters.command(["help"]) & filters.private)
async def help(client, message):
    await message.reply_text(
        text=Script.HELP_MSG,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("BACK", callback_data="start_data"),
                    InlineKeyboardButton("ABOUT", callback_data="about_data"),
                ],
                [
                    InlineKeyboardButton(
                        "⭕️SUPPORT⭕️", url="https://t.me/gunaya001")
                ]
            ]
        ),
        reply_to_message_id=message.id
    )


@trojanz.on_message(filters.command(["about"]) & filters.private)
async def about(client, message):
    await message.reply_text(
        text=Script.ABOUT_MSG,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("BACK", callback_data="help_data"),
                    InlineKeyboardButton("START", callback_data="start_data"),
                ],
                [
                    InlineKeyboardButton(
                        "SOURCE CODE", url="https://github.com/pachax001/Stream-Extract-Bot")
                ]
            ]
        ),
        reply_to_message_id=message.id
    )

@trojanz.on_message(filters.command(["log"]) & filters.private & filters.user(Config.OWNER_ID))
async def log(client, message):
    try:
        with open('log.txt', 'rb') as f:
            await client.send_document(message.chat.id, document=f, caption="Log file")
    except:
        await message.reply_text("No log file found")

async def is_ffmpeg_running():
    # Check if ffmpeg process is running
    try:
        subprocess.run(["pgrep", "ffmpeg"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

@trojanz.on_message(filters.command(["restart"]) & filters.private & filters.user(Config.OWNER_ID))
async def restart(client, message):
    try:
        if await is_ffmpeg_running():
            await asyncio.create_subprocess_exec("pkill", "-9", "-f", "ffmpeg")
        await message.reply_text("Restarting the bot...")
        await asyncio.create_subprocess_exec("python3", "update.py")
        os.execl(sys.executable, sys.executable, "main.py")
    except Exception as e:
        logger.error("Error in restart: %s", e)