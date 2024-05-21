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
import asyncio


LOG_CHANNEL = Config.LOG_CHANNEL
BOT_USERNAME = Config.BOT_USERNAME
async def upload_audio(client, message, file_loc, username, userid, file_name):
    
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
        await asyncio.sleep(5)
        logger.info(f"Uploading extracted stream...")
        await client.send_audio(
            chat_id=message.chat.id,
            audio=file_loc,
            thumb=thumb,
            caption=f"Uploaded by {BOT_USERNAME}",
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
        logger.error(f"Error while uploading extracted stream for {file_name}: {e}")
        await msg.edit_text(f"**Some Error Occurred for {file_name} while uploading audio. See Logs for More Info.**")
        await clean_up(file_loc, None, file_loc)
        return
    try:
        if LOG_CHANNEL is None or LOG_CHANNEL == "":
            return
        await asyncio.sleep(5)
        logger.info(f"Uploading extracted stream to log channel...")
        await client.send_audio(
            chat_id=LOG_CHANNEL,
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
        logger.error(f"Error while uploading extracted stream to log channel from {file_name}: {e}")
        await msg.edit_text(f"**Some Error Occurred While Sending {file_name} to Log Channel. See Logs for More Info.**")
        await clean_up(file_loc, None, file_loc)   
        return

    await msg.delete()

    await clean_up(file_loc, None, file_loc)    


async def upload_subtitle(client, message, file_loc,username,userid,file_name):
    
    msg = await message.edit_text(
        text="**Uploading extracted subtitle...**",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Progress", callback_data="progress_msg")]])
    )

    c_time = time.time() 

    try:
        await asyncio.sleep(5)
        logger.info(f"Uploading extracted subtitle...")
        await client.send_document(
            chat_id=message.chat.id,
            document=file_loc,
            caption=f"Uploaded by {BOT_USERNAME}",
            progress=progress_func,
            progress_args=(
                "**Uploading extracted subtitle...**",
                msg,
                c_time
            )
        )
    except Exception as e:
        logger.error(f"Error while uploading extracted subtitle from {file_name}: {e}")
        await msg.edit_text(f"**Some Error Occurred for {file_name} while extracting subtitle. See Logs for More Info.**")
        await clean_up(file_loc, None, file_loc)
        return
    try:
        if LOG_CHANNEL is None or LOG_CHANNEL == "":
            return
        await asyncio.sleep(5)
        logger.info(f"Uploading extracted subtitle to log channel...")
        await client.send_document(
            chat_id=LOG_CHANNEL,
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
        logger.error(f"Error while uploading extracted subtitle from {file_name} to log channel: {e}")   
        await msg.edit_text(f"**Some Error Occurred while sending {file_name} to log channel. See Logs for More Info.**")   
        return

    await msg.delete()
    await clean_up(file_loc, None, file_loc)        
