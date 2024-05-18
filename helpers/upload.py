#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @trojanzhex


import time
from pyrogram import Client, filters
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

from helpers.tools import clean_up
from helpers.progress import progress_func
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from helpers.logger import logger


log_channel = Config.LOG_CHANNEL
bot_username = Config.BOT_USERNAME
async def upload_audio(client, message, file_loc, username, userid):
    
    msg = await message.edit_text(
        text="**Uploading extracted stream...**",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Progress", callback_data="progress_msg")]])
    )

    title = None
    artist = None
    thumb = None
    duration = 0

    metadata = extractMetadata(createParser(file_loc))
    if metadata and metadata.has("title"):
        title = metadata.get("title")
    if metadata and metadata.has("artist"):
        artist = metadata.get("artist")
    if metadata and metadata.has("duration"):
        duration = metadata.get("duration").seconds

    c_time = time.time()    

    try:
        logger.info(f"Uploading extracted stream...")
        await client.send_audio(
            chat_id=message.chat.id,
            audio=file_loc,
            thumb=thumb,
            caption=f"Uploaded by @{bot_username}",
            title=title,
            performer=artist,
            duration=duration,
            progress=progress_func,
            progress_args=(
                "**Uploading extracted stream...**",
                msg,
                c_time
            )
        )
    except Exception as e:
        logger.error(f"Error while uploading extracted stream: {e}")
        await msg.edit_text("**Some Error Occurred. See Logs for More Info.**")
        await clean_up(file_loc, None, file_loc)
        return
    try:
        logger.info(f"Uploading extracted stream to log channel...")
        await client.send_audio(
            chat_id=log_channel,
            audio=file_loc,
            thumb=thumb,
            caption=f"Extracted by: <a href='tg://user?id={userid}'>{username}</a>",
            title=title,
            performer=artist,
            duration=duration,
            progress=progress_func,
            progress_args=(
                "**Uploading extracted stream...**",
                msg,
                c_time
            )
        )
    except Exception as e:
        logger.error(f"Error while uploading extracted stream to log channel: {e}")
        await msg.edit_text("**Some Error Occurred. See Logs for More Info.**")
        await clean_up(file_loc, None, file_loc)   
        return

    await msg.delete()
    await clean_up(file_loc, None, file_loc)    


async def upload_subtitle(client, message, file_loc,username,userid):
    
    msg = await message.edit_text(
        text="**Uploading extracted subtitle...**",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Progress", callback_data="progress_msg")]])
    )

    c_time = time.time() 

    try:
        await client.send_document(
            chat_id=message.chat.id,
            document=file_loc,
            caption=f"Uploaded by @{bot_username}",
            progress=progress_func,
            progress_args=(
                "**Uploading extracted subtitle...**",
                msg,
                c_time
            )
        )
        await client.send_document(
            chat_id=log_channel,
            document=file_loc,
            caption=f"Extracted by: <a href='tg://user?id={userid}'>{username}</a>",
            progress=progress_func,
            progress_args=(
                "**Uploading extracted subtitle...**",
                msg,
                c_time
            )
        )
    except Exception as e:
        logger.error(f"Error while uploading extracted subtitle: {e}")   
        await msg.edit_text("**Some Error Occurred. See Logs for More Info.**")   
        return

    await msg.delete()
    await clean_up(file_loc, None, file_loc)        
