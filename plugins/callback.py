from pyrogram import filters
from pyrogram import Client as trojanz
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from script import Script

from helpers.progress import PRGRS,PRGRS_CALLBACK
from helpers.tools import clean_up
from helpers.download import download_file, DATA
from helpers.ffmpeg import extract_audio, extract_subtitle
from helpers.logger import logger

@trojanz.on_callback_query()
async def cb_handler(client, query):

    if query.data == "start_data":
        await query.answer()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("HELP", callback_data="help_data"),
                InlineKeyboardButton("ABOUT", callback_data="about_data")],
            [InlineKeyboardButton("⭕️OWNER⭕️", url="https://t.me/gunaya001")]
        ])

        await query.message.edit_text(
            Script.START_MSG.format(query.from_user.mention),
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return


    elif query.data == "help_data":
        await query.answer()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("BACK", callback_data="start_data"),
                InlineKeyboardButton("ABOUT", callback_data="about_data")],
            [InlineKeyboardButton("⭕️ SUPPORT ⭕️", url="https://t.me/gunaya001")]
        ])

        await query.message.edit_text(
            Script.HELP_MSG,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return


    elif query.data == "about_data":
        await query.answer()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("BACK", callback_data="help_data"),
                InlineKeyboardButton("START", callback_data="start_data")],
            [InlineKeyboardButton("SOURCE CODE", url="https://github.com/pachax001/Stream-Extract-Bot")]
        ])

        await query.message.edit_text(
            Script.ABOUT_MSG,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return


    elif query.data == "download_file":
        await query.answer()
        await query.message.delete()
        await download_file(client, query.message)


    elif query.data == "progress_msg_download":
        unique_id = f"{query.message.chat.id}_{query.message.id}_download"
        #logger.info(f"Progress for in callback main {unique_id}: {PRGRS[unique_id]}")
        try:
            if unique_id not in PRGRS_CALLBACK:
                await query.answer(
                    "Processing your file...",
                    show_alert=True
                )
                return
            msg = "Progress Details...\n\nCompleted : {current}\nTotal Size : {total}\nSpeed : {speed}\nProgress : {progress:.2f}%\nElapsed Time : {elapsed}\nETA: {eta}"
            #ud_type = DATA['ud_type']
            
            logger.info(f"Progress for in callback {unique_id}: {PRGRS[unique_id]}")
            await query.answer(
                msg.format(
                    **PRGRS_CALLBACK[unique_id]
                ),
                show_alert=True
            )
        except Exception as e:
            logger.error(f"Error while getting progress: {e}")
            logger.info(f"Progress for in callback {unique_id}: {PRGRS[unique_id]}")
            await query.answer(
                "Processing your file...",
                show_alert=True
            )
    elif query.data == "progress_msg_upload":
        unique_id = f"{query.message.chat.id}_{query.message.id}_upload"
        #logger.info(f"Progress for in callback main {unique_id}: {PRGRS[unique_id]}")
        try:
            if unique_id not in PRGRS_CALLBACK:
                await query.answer(
                    "Processing your file...",
                    show_alert=True
                )
                return
            msg = "Progress Details...\n\nCompleted : {current}\nTotal Size : {total}\nSpeed : {speed}\nProgress : {progress:.2f}%\nElapsed Time : {elapsed}\nETA: {eta}"
            #ud_type = DATA['ud_type']
            
            logger.info(f"Progress for in callback {unique_id}: {PRGRS[unique_id]}")
            await query.answer(
                msg.format(
                    **PRGRS_CALLBACK[unique_id]
                ),
                show_alert=True
            )
        except Exception as e:
            logger.error(f"Error while getting progress: {e}")
            logger.info(f"Progress for in callback {unique_id}: {PRGRS[unique_id]}")
            await query.answer(
                "Processing your file...",
                show_alert=True
            )


    elif query.data == "close": 
        await query.message.delete()  
        await query.answer(
                "Cancelled...",
                show_alert=True
            ) 


    elif query.data.startswith('audio'):
        await query.answer()
        try:
            stream_type, mapping, keyword = query.data.split('_')
            data = DATA[keyword][int(mapping)]
            await extract_audio(client, query.message, data)
        except Exception as e:
            await query.message.edit_text("**Details Not Found**")
            logger.error(f"Error while extracting audio: {e}")   


    elif query.data.startswith('subtitle'):
        await query.answer()
        try:
            stream_type, mapping, keyword = query.data.split('_')
            data = DATA[keyword][int(mapping)]
            await extract_subtitle(client, query.message, data)
        except Exception as e:
            await query.message.edit_text("**Details Not Found**")
            logger.error(f"Error while extracting subtitle: {e}")  


    elif query.data.startswith('cancel'):
        try:
            query_type, mapping, keyword = query.data.split('_')
            data = DATA[keyword][int(mapping)] 
            await clean_up(data['location'], None, data['file_name'])  
            await query.message.edit_text("**Cancelled...**")
            await query.answer(
                "Cancelled...",
                show_alert=True
            ) 
        except Exception as e:
            await query.answer() 
            await query.message.edit_text("**Details Not Found**") 
            logger.error(f"Error while cancelling: {e}")       
