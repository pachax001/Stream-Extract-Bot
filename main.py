import os
from pyrogram import Client

from config import Config
from helpers.logger import logger

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

@app.on_startup
async def on_startup():
    await edit_restart_message()

if __name__ == "__main__":
    logger.info("Bot has started.")
    app.run()
