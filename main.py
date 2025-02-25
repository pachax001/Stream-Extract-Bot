import os
import asyncio
from pyrogram import Client
from config import Config
from helpers.logger import logger
import datetime
import pytz
from pyrogram.types import User

async def edit_restart_message(app):
    
    # This function edits a restart message if it exists
    try:
        current_time = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        date_formatted = current_time.strftime("%d/%m/%y")
        time_formatted = current_time.strftime("%I:%M:%S %p")


        version = "v1.0.8.m"

        restart_message = f"⌬ Restarted Successfully!\n┠ Date: {date_formatted}\n┠ Time: {time_formatted}\n┠ TimeZone: Asia/Kolkata\n┖ Version: {version}"
        if os.path.exists("restart_msg_id.txt"):
            with open("restart_msg_id.txt", "r") as f:
                message_id = int(f.read().strip())
            
            await app.edit_message_text(
                chat_id=Config.OWNER_ID,  #
                message_id=message_id,
                text=restart_message
            )
            if Config.LOG_CHANNEL is not None and Config.LOG_CHANNEL != "":
                try:
                    await app.send_message(
                        chat_id=int(Config.LOG_CHANNEL),
                        text=f"Restarted Successfully!\nDate: {date_formatted}\nTime: {time_formatted}\nTimeZone: Asia/Kolkata\nVersion: {version}"
                    )
                except Exception as e:
                    logger.error("Failed to send restart message to LOG_CHANNEL: %s", e)
                    pass
            if Config.LOG_MEDIA_CHANNEL is not None and Config.LOG_MEDIA_CHANNEL != "":
                try:
                    await app.send_message(
                        chat_id=int(Config.LOG_MEDIA_CHANNEL),
                        text=f"Restarted Successfully!\nDate: {date_formatted}\nTime: {time_formatted}\nTimeZone: Asia/Kolkata\nVersion: {version}"
                    )
                except Exception as e:
                    logger.error("Failed to send restart message to LOG_MEDIA_CHANNEL: %s", e)
                    pass

            logger.info("Restart message edited successfully.")
            os.remove("restart_msg_id.txt")
        else:
            logger.info("No restart message found.")
    except Exception as e:
        logger.error("Failed to edit restart message: %s", e)

async def main():
    app = Client(
        "TroJanz",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.APP_ID,
        api_hash=Config.API_HASH,
        plugins=dict(root="plugins"),
        workers=300,
        max_concurrent_transmissions=100
    )

    try:
        
        

        # Start the bot
        await app.start()
        me = await app.get_me()
        logger.info(f"{me.username} has started.")
        await edit_restart_message(app)
        # Keep the application running
        await asyncio.Event().wait()

    except Exception as e:
        logger.error("Error occurred: %s", e)
        await app.stop()

if __name__ == "__main__":
    logger.info("Starting bot...")
    asyncio.run(main())
