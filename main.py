import os
import asyncio
from pyrogram import Client
from config import Config
from helpers.logger import logger

async def edit_restart_message():
    if os.path.exists("restart_msg_id.txt"):
        try:
            with open("restart_msg_id.txt", "r") as f:
                message_id = int(f.read().strip())
            
            await app.edit_message_text(
                chat_id=Config.OWNER_ID,  # Assumes OWNER_ID is the chat where the message was sent
                message_id=message_id,
                text="Restarted successfully!"
            )
        except Exception as e:
            logger.error("Failed to edit restart message: %s", e)
        finally:
            os.remove("restart_msg_id.txt")

if __name__ == "__main__":
    logger.info("Starting bot...")

    # Ensure an event loop is created and set as the current event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
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
        logger.info("Running edit_restart_message before starting the bot...")
        loop.run_until_complete(edit_restart_message())
        logger.info("edit_restart_message completed.")

        logger.info("Starting the bot...")
        
        # Start the bot
        app.run()
        logger.info("Bot has started.")
        
        # Keep the event loop running indefinitely
        loop.run_forever()
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    
    except Exception as e:
        logger.error("Error occurred: %s", e)
    
    finally:
        # Clean up resources
        app.stop()
        loop.close()
