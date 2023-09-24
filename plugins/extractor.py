#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @trojanzhex


from pyrogram import filters
from pyrogram import Client as trojanz
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from user_info import user_id, user_first_name

from config import Config
from script import Script


@trojanz.on_message(filters.private & (filters.document | filters.video))
async def confirm_dwnld(client, message):
    global user_id
    global user_first_name
    if message.from_user.id not in Config.AUTH_USERS:
        return
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    media = message
    filetype = media.document or media.video

    if filetype.mime_type.startswith("video/"):
        await message.reply_text(
            "**What you want me to do??**",
            quote=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="DOWNLOAD and PROCESS", callback_data="download_file")],
                [InlineKeyboardButton(text="CANCEL", callback_data="close")]
            ])
        )
    else:
        await message.reply_text(
            "Invalid Media",
            quote=True
        )
