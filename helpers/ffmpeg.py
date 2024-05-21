#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @trojanzhex


from helpers.tools import execute, clean_up
from helpers.upload import upload_audio, upload_subtitle
from helpers.logger import logger

async def extract_audio(client, message, data):
    file_name = data.get('file_name', 'unknown_file')
    user_id = data.get('user_id', 'unknown_user')
    user_name = data.get('user_first_name', 'unknown_user')
    logger.info(f"User {user_id} - {user_name} requested to download audio from {file_name}")
    logger.info(f"Extracting audio from {file_name}...")
    await message.edit_text(f"Extracting audio from {file_name}...")

    dwld_loc = data['location']
    out_loc = data['location'] + ".mp3"

    if data['name'] == "mp3":
        try:
            out, err, rcode, pid = await execute(f"ffmpeg -i '{dwld_loc}' -map 0:{data['map']} -c copy '{out_loc}' -y")
            if rcode != 0:
                await message.edit_text(f"**Error Occured for {file_name}. See Logs for more info.**")
                logger.error("Error Occured",err)
                await clean_up(dwld_loc, out_loc, file_name)
                return
        except Exception as err:  # Corrected syntax for exception handling
            await message.edit_text(f"**Error Occurred for {file_name}. See Logs for more info.**")
            #logger.error("Exception error",err)
            logger.error("Error Occurred", exc_info=True)
            await clean_up(dwld_loc, out_loc,file_name)
            return
    else:
        try:
            out, err, rcode, pid = await execute(f"ffmpeg -i '{dwld_loc}' -map 0:{data['map']} '{out_loc}' -y")
            if rcode != 0:
                await message.edit_text(f"**Error Occured for {file_name}. See Logs for more info.**")
                logger.error("Error Occured",err)
                await clean_up(dwld_loc, out_loc, file_name)
                return
        except Exception as err:  # Corrected syntax for exception handling
            await message.edit_text(f"**Error Occurred for {file_name}. See Logs for more info.**")
            #logger.error("Exception error",err)
            logger.error("Error Occurred", exc_info=True)
            await clean_up(dwld_loc, out_loc, file_name)
            return
    await clean_up(dwld_loc,None, file_name)
    await upload_audio(client, message, out_loc,user_name,user_id,file_name)



async def extract_subtitle(client, message, data):
    file_name = data.get('file_name', 'unknown_file')
    user_id = data.get('user_id', 'unknown_user')
    user_name = data.get('user_first_name', 'unknown_user')
    logger.info(f"User {user_id} - {user_name} requested to download subtitle from {file_name}")
    await message.edit_text(f"Extracting subtitle from {file_name}...")
    logger.info(f"Extracting subtitle from {file_name}...")

    dwld_loc = data['location']
    out_loc = data['location'] + ".srt"   
    try:
        out, err, rcode, pid = await execute(f"ffmpeg -i '{dwld_loc}' -map 0:{data['map']} '{out_loc}' -y")
        if rcode != 0:
            await message.edit_text(f"**Error Occurred for {file_name}. See Logs for more info.**")
            logger.error("Error Occurred", exc_info=True)  # Use exc_info=True to log the exception details
            await clean_up(dwld_loc, out_loc, file_name)
            return
    except Exception as err:  # Corrected syntax for exception handling
        await message.edit_text(f"**Error Occurred for {file_name}. See Logs for more info.**")
        #logger.error("Exception error",err)
        logger.error("Error Occurred", exc_info=True)
        await clean_up(dwld_loc, out_loc, file_name)
        return
    await clean_up(dwld_loc,None, file_name)  
    await upload_subtitle(client, message, out_loc,user_name,user_id, file_name)
    
