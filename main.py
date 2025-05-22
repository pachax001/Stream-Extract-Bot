import asyncio
import datetime
from pathlib import Path

import pytz
from pyrogram import Client
from helpers.logger import logger
from config import Config

# Constants
RESTART_FILE = Path("restart_msg_id.txt")
VERSION = "v1.1.1.m"
TIMEZONE = pytz.timezone("Asia/Kolkata")

async def edit_restart_message(app: Client) -> None:
    """
    Edit the restart notification message for the bot owner and log channels if present.
    """
    try:
        # Current timestamp in configured timezone
        now = datetime.datetime.now(TIMEZONE)
        restart_text = (
            f"⌬ Restarted Successfully!\n"
            f"┠ Date: {now:%d/%m/%y}\n"
            f"┠ Time: {now:%I:%M:%S %p}\n"
            f"┠ TimeZone: {TIMEZONE.zone}\n"
            f"┖ Version: {VERSION}"
        )

        if not RESTART_FILE.exists():
            logger.info("No restart message found.")
            return

        message_id = int(RESTART_FILE.read_text().strip())

        # Edit message to bot owner
        await app.edit_message_text(
            chat_id=Config.OWNER_ID,
            message_id=message_id,
            text=restart_text
        )

        # Send to log channels (if configured)
        for channel in {Config.LOG_CHANNEL, Config.LOG_MEDIA_CHANNEL}:
            if channel:
                try:
                    await app.send_message(
                        chat_id=int(channel),
                        text=restart_text
                    )
                except Exception as e:
                    logger.error(f"Failed to send restart message to {channel}: {e}")

        logger.info("Restart message handled successfully.")
        RESTART_FILE.unlink()

    except Exception as e:
        logger.error(f"Failed to edit restart message: {e}")

async def main() -> None:
    """
    Initialize and run the Pyrogram bot client.
    """
    app = Client(
        "TroJanz",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.APP_ID,
        api_hash=Config.API_HASH,
        plugins=dict(root="plugins"),
        workers=300,
        max_concurrent_transmissions=100,
    )

    try:
        await app.start()
        me = await app.get_me()
        logger.info(f"{me.username} has started.")
        await edit_restart_message(app)

        # Keep the bot running until manually stopped
        await asyncio.Event().wait()

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        await app.stop()

if __name__ == "__main__":
    logger.info("Starting bot...")
    asyncio.run(main())
