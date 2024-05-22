#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @trojanzhex


import time
import json
from pyrogram import filters
from pyrogram import Client as trojanz
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from helpers.progress import progress_func
from helpers.tools import execute, clean_up
from helpers.logger import logger
from config import Config
from helpers.progress import humanbytes
from pyrogram.enums import ParseMode
import pyrogram.errors as perrors
import asyncio
import os
LOG_MEDIA_CHANNEL = Config.LOG_MEDIA_CHANNEL
LOG_CHANNEL = Config.LOG_CHANNEL
LOG_MODE = False
if LOG_MEDIA_CHANNEL  is None or LOG_MEDIA_CHANNEL == "":
    LOG_MEDIA_CHANNEL = LOG_CHANNEL
    LOG_MODE = True
else:
    LOG_MEDIA_CHANNEL = LOG_MEDIA_CHANNEL
    LOG_MODE = True

DATA = {}

async def download_file(client, message):
    media = message.reply_to_message
    filetype = media.document or media.video
    user_id = message.reply_to_message.from_user.id
    user_first_name = message.reply_to_message.from_user.first_name
    #user_id = message.from_user.id  # Set the user ID
    try:
        user_first_name = message.reply_to_message.from_user.first_name  # Set the first name
    except:
        user_first_name = "Unknown"
    try:
        username = message.reply_to_message.from_user.username  # Set the username
    except:
        username = "Unknown"
    try:
        full_name = message.reply_to_message.from_user.full_name  # Set the full name
    except:
        full_name = "Unknown"
    file_name = filetype.file_name if filetype else "unknown_file"
    originalfilesize = humanbytes(filetype.file_size) if filetype else 0
    logger.info(f"Original file size: {originalfilesize}")

    caption = "File Name: <code>{}</code>\n".format(file_name)
    caption += "File Size: <code>{}</code>\n".format(humanbytes(filetype.file_size))
    caption += "Forward User Details:\n"
    caption += "User ID: <code>{}</code>\n".format(user_id)
    caption += "First Name: <a href='tg://user?id={}'>{}</a>\n".format(user_id, user_first_name)
    caption += "Username: @{}\n".format(username)
    caption += "Full Name: {}\n".format(full_name)
    if media.empty:
        await message.reply_text('Why did you delete that?? 😕', True)
        return
    
    file_name = filetype.file_name if filetype else "unknown_file"
    logger.info(f"Send file to download {file_name} by {user_id} - {user_first_name}")
    try:
        msg = await client.send_message(
            chat_id=message.chat.id,
            text=f"**Downloading {file_name} to server...**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="Check Progress", callback_data="progress_msg")]
            ]),
            reply_to_message_id=media.id
        )
    except Exception as e:
        logger.error(f"Error while sending message: {e}")
        await message.reply_text("Some error occured. Please try again later.")
        return
    

    c_time = time.time()
    MAX_RETRIES = 5
    retries = 0
    while retries < MAX_RETRIES:
        try:
            download_location = await client.download_media(
                message=media,
                progress=progress_func,
                progress_args=(
                    f"**Downloading {file_name} to server...**",
                    msg,
                    c_time
                )
            )
            if download_location:
                downloaded_file_size = humanbytes(os.path.getsize(download_location))
                logger.info(f"Downloaded file size: {downloaded_file_size}")
                if originalfilesize != downloaded_file_size:
                    logger.error(f"File size mismatch. Original: {originalfilesize}, Downloaded: {downloaded_file_size}")
                    await msg.edit_text(f"File size mismatch. Original: {originalfilesize}, Downloaded: {downloaded_file_size}")
                    await clean_up(download_location, None, file_name)
                    retries += 1
                    logger.info(f"Retrying download {retries}/{MAX_RETRIES}...")
                    continue
                else:
                    await msg.edit_text(f"Processing {file_name}....")
                    logger.info(f"Downloaded {file_name} to server. Time taken: {time.time() - c_time} seconds.")
                    try:
                        if LOG_MODE:
                            await trojanz.copy_message(client,LOG_MEDIA_CHANNEL, media.chat.id, media.id,caption,parse_mode=ParseMode.HTML)
                            await asyncio.sleep(5)
                            
                    except perrors.bad_request_400.UsernameNotOccupied as e:
                        #logger.error(f"Error while forwarding media to log channel: Username not occupied")
                        pass
                    except Exception as e:
                        logger.error(f"Error while forwarding media to log channel: {e}")
                    try:
                        output = await execute(f"ffprobe -hide_banner -show_streams -print_format json '{download_location}'")
                    except Exception as e:
                        logger.error(f"Error while executing ffprobe: {e}")
                        await clean_up(download_location, None, file_name)
                        await msg.edit_text(f"Some Error Occured while Fetching Details of {file_name}")
                        return

                    details = json.loads(output[0])
                    buttons = []
                    DATA[f"{message.chat.id}-{msg.id}"] = {}
                    for stream in details["streams"]:
                        mapping = stream["index"]
                        stream_name = stream["codec_name"]
                        stream_type = stream["codec_type"]
                        if stream_type in ("audio", "subtitle"):
                            pass
                        else:
                            continue
                        try: 
                            lang = stream["tags"]["language"]
                        except:
                            lang = mapping
                        
                        DATA[f"{message.chat.id}-{msg.id}"][int(mapping)] = {
                            "map" : mapping,
                            "name" : stream_name,
                            "type" : stream_type,
                            "lang" : lang,
                            "location" : download_location,
                            "file_name" : file_name,
                            "user_id" : user_id,
                            "user_first_name" : user_first_name
                        }
                        buttons.append([
                            InlineKeyboardButton(
                                f"{stream_type.upper()} - {str(lang).upper()}", f"{stream_type}_{mapping}_{message.chat.id}-{msg.id}"
                            )
                        ])

                    buttons.append([
                        InlineKeyboardButton("CANCEL",f"cancel_{mapping}_{message.chat.id}-{msg.id}")
                    ])    

                    await msg.edit_text(
                        f"**Select the Stream to be Extracted for {file_name}**",
                        reply_markup=InlineKeyboardMarkup(buttons)
                        )
                    return
        except perrors.MessageNotModified:
            pass
        except Exception as e:
            logger.error(f"Error while downloading {file_name}: {e}")
            await msg.edit_text(f"Error while downloading {file_name}")
            clean_up(download_location +".temp", None, file_name)
            return
    logger.error(f"Failed to download {file_name} after {MAX_RETRIES} retries.")
    await msg.edit_text(f"Failed to download {file_name} after {MAX_RETRIES} retries.")
    return



