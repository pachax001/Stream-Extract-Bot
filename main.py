import os
import asyncio
from pyrogram import Client
from config import Config
from helpers.logger import logger

async def edit_restart_message():
    # This function edits a restart message if it exists
    try:
        if os.path.exists("restart_msg_id.txt"):
            with open("restart_msg_id.txt", "r") as f:
                message_id = int(f.read().strip())
            
            await app.edit_message_text(
                chat_id=Config.OWNER_ID,  # Assumes OWNER_ID is the chat where the message was sent
                message_id=message_id,
                text="Restarted successfully!"
            )
            logger.info("Restart message edited successfully.")
            os.remove("restart_msg_id.txt")
        else:
            logger.info("No restart message found.")
    except Exception as e:
        logger.error("Failed to edit restart message: %s", e)

async def main():
    # Initialize your Pyrogram client
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
        # Run the edit_restart_message function before starting the bot
        await edit_restart_message()

        # Start the bot
        await app.start()
        logger.info("Bot has started.")

    except Exception as e:
        logger.error("Error occurred: %s", e)
        await app.stop()

if __name__ == "__main__":
    logger.info("Starting bot...")
    asyncio.run(main())
