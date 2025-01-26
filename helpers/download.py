import time
import json
import shutil
from pyrogram import Client as trojanz
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from helpers.progress import progress_func, ACTIVE_DOWNLOADS,PRGRS
from helpers.tools import execute, clean_up
from helpers.logger import logger
from config import Config
from helpers.progress import humanbytes
from pyrogram.enums import ParseMode
import pyrogram.errors as perrors
import asyncio
import os

MAX_DOWNLOAD_LIMIT = Config.MAX_DOWLOAD_LIMIT  # e.g., 3 for a maximum of 3 concurrent downloads
CURRENT_DOWNLOADS = 0  # Global counter

# Convert threshold from GB to bytes
THRESHOLD_IN_BYTES = Config.THRESHOLD * 1024 * 1024 * 1024

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
    global CURRENT_DOWNLOADS

    # 1) Check concurrency first
    if CURRENT_DOWNLOADS >= MAX_DOWNLOAD_LIMIT:
        await message.reply_text(
            f"**Concurrent Download Limit Reached**\n\n"
            f"We already have {CURRENT_DOWNLOADS} downloads in progress.\n"
            f"Please wait or try again later."
        )
        return

    # Otherwise, we can proceed
    CURRENT_DOWNLOADS += 1
    try:
        media = message.reply_to_message
        filetype = media.document or media.video
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name or "Unknown"
        username = message.reply_to_message.from_user.username or "Unknown"
        full_name = message.reply_to_message.from_user.full_name or "Unknown"
        unique_id = f"{message.chat.id}_{message.id}_download"

        if media.empty:
            await message.reply_text('Why did you delete that?? 😕', True)
            return

        file_name = filetype.file_name if filetype else "unknown_file"
        originalfilesize = humanbytes(filetype.file_size) if filetype else 0
        logger.info(f"Original file size: {originalfilesize}")

        caption = (
            f"File Name: <code>{file_name}</code>\n"
            f"File Size: <code>{humanbytes(filetype.file_size)}</code>\n"
            f"Forward User Details:\n"
            f"User ID: <code>{user_id}</code>\n"
            f"First Name: <a href='tg://user?id={user_id}'>{user_first_name}</a>\n"
            f"Username: @{username}\n"
            f"Full Name: {full_name}\n"
        )

        # 2) Check free disk space before download
        total, used, free = shutil.disk_usage("/") 
        logger.info(f"Free disk space: {humanbytes(free)}; Threshold: {humanbytes(THRESHOLD_IN_BYTES)}")
        
        if free < THRESHOLD_IN_BYTES:
            await message.reply_text(
                f"Cannot download **{file_name}**.\n\n"
                f"Free disk space is **{humanbytes(free)}** which is below the threshold "
                f"(**{humanbytes(THRESHOLD_IN_BYTES)}**)."
            )
            return
        ACTIVE_DOWNLOADS[unique_id] = {
        "file_name": file_name,
        "user_id": message.from_user.id,
        "start_time": time.time()
    }
        logger.info(f"Downloading {file_name} to server...")
        logger.info(f"Current downloads: {CURRENT_DOWNLOADS}")
        logger.info(f"Active downloads in download.py: {ACTIVE_DOWNLOADS}")

        try:
            msg = await client.send_message(
                chat_id=message.chat.id,
                text=f"**Downloading {file_name} to server...**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="Check Progress", callback_data="progress_msg_download")]
                ]),
                reply_to_message_id=media.id
            )
        except Exception as e:
            logger.error(f"Error while sending message: {e}")
            await message.reply_text("Some error occurred. Please try again later.")
            return

        c_time = time.time()
        MAX_RETRIES = 5
        retries = 0
        download_location = None
        
        while retries < MAX_RETRIES:
            try:
                download_location = await client.download_media(
                    message=media,
                    progress=progress_func,
                    progress_args=(
                       "download",
                        msg,
                        c_time
                    )
                )
                if download_location:
                    downloaded_file_size = humanbytes(os.path.getsize(download_location))
                    logger.info(f"Downloaded file size: {downloaded_file_size}")

                    if originalfilesize != downloaded_file_size:
                        logger.error(
                            f"File size mismatch. Original: {originalfilesize}, "
                            f"Downloaded: {downloaded_file_size}"
                        )
                        await msg.edit_text(
                            f"File size mismatch.\nOriginal: {originalfilesize}, "
                            f"Downloaded: {downloaded_file_size}"
                        )
                        await clean_up(download_location, None, file_name)
                        retries += 1
                        logger.info(f"Retrying download {retries}/{MAX_RETRIES}...")
                        continue
                    else:
                        await msg.edit_text(f"Processing {file_name}....")
                        logger.info(
                            f"Downloaded {file_name} to server. Time taken: "
                            f"{time.time() - c_time} seconds."
                        )

                        # Forward (or copy) the file to LOG channel if needed
                        try:
                            if LOG_MODE:
                                await trojanz.copy_message(
                                    client,
                                    LOG_MEDIA_CHANNEL,
                                    media.chat.id,
                                    media.id,
                                    caption=caption,
                                    parse_mode=ParseMode.HTML
                                )
                                await asyncio.sleep(5)
                        except perrors.bad_request_400.UsernameNotOccupied:
                            pass
                        except Exception as e:
                            logger.error(f"Error while forwarding media to log channel: {e}")

                        # ffprobe for streams
                        try:
                            output = await execute(
                                f"ffprobe -hide_banner -show_streams -print_format json '{download_location}'"
                            )
                        except Exception as e:
                            logger.error(f"Error while executing ffprobe: {e}")
                            await clean_up(download_location, None, file_name)
                            await msg.edit_text(
                                f"Some Error Occurred while Fetching Details of {file_name}"
                            )
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
                                "map": mapping,
                                "name": stream_name,
                                "type": stream_type,
                                "lang": lang,
                                "location": download_location,
                                "file_name": file_name,
                                "user_id": user_id,
                                "user_first_name": user_first_name,
                                
                            }
                            buttons.append([
                                InlineKeyboardButton(
                                    f"{stream_type.upper()} - {str(lang).upper()}", 
                                    f"{stream_type}_{mapping}_{message.chat.id}-{msg.id}"
                                )
                            ])

                        buttons.append([
                            InlineKeyboardButton("CANCEL", f"cancel_{mapping}_{message.chat.id}-{msg.id}")
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
                if download_location:
                    clean_up(download_location, None, file_name)
                return

        # If maximum retries exceeded
        logger.error(f"Failed to download {file_name} after {MAX_RETRIES} retries.")
        await msg.edit_text(f"Failed to download {file_name} after {MAX_RETRIES} retries.")
        return

    finally:
        # Decrement the counter in a finally block so it happens even if an error occurs
        CURRENT_DOWNLOADS -= 1
        if unique_id in ACTIVE_DOWNLOADS:
            del ACTIVE_DOWNLOADS[unique_id]
        if unique_id in PRGRS:
            del PRGRS[unique_id]
