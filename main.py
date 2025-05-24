import asyncio
import datetime
from pathlib import Path

import pytz
from pyrogram import Client
from pyrogram.errors import RPCError  # Import for specific Pyrogram errors
from helpers.logger import logger
from config import Config

# Constants
RESTART_FILE = Path("restart_msg_id.txt")
VERSION = "v1.1.2.m"
TIMEZONE = pytz.timezone("Asia/Kolkata")

async def edit_restart_message(app: Client) -> None:
    """
    Edit the restart notification message for the bot owner and log channels if present.
    """
    if not RESTART_FILE.exists():
        logger.debug("No restart message found.")
        return

    message_id_str = ""
    try:
        message_id_str = RESTART_FILE.read_text().strip()
        message_id = int(message_id_str)

        # Current timestamp in configured timezone
        now = datetime.datetime.now(TIMEZONE)
        restart_text = (
            f"⌬ Restarted Successfully!\n"
            f"┠ Date: {now:%d/%m/%y}\n"
            f"┠ Time: {now:%I:%M:%S %p}\n"
            f"┠ TimeZone: {TIMEZONE.zone}\n"
            f"┖ Version: {VERSION}"
        )

        owner_id = -1
        try:
            owner_id = int(Config.OWNER_ID)
        except ValueError:
            logger.error(f"Invalid OWNER_ID: {Config.OWNER_ID}. Cannot send restart message to owner.")
            # Optionally, decide if you want to proceed without sending to owner or return

        if owner_id != -1 : # Proceed if owner_id is valid
            try:
                await app.edit_message_text(
                    chat_id=owner_id,
                    message_id=message_id,
                    text=restart_text
                )
            except RPCError as e:
                logger.error(f"Pyrogram RPCError while editing message for owner {owner_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to edit restart message for owner {owner_id}: {e}")

        # Send to log channels (if configured)
        log_channels = {Config.LOG_CHANNEL, Config.LOG_MEDIA_CHANNEL}
        for channel_str in log_channels:
            if channel_str: # Ensure channel_str is not None or empty
                try:
                    channel_id = int(channel_str)
                    await app.send_message(
                        chat_id=channel_id,
                        text=restart_text
                    )
                except ValueError:
                    logger.error(f"Invalid channel ID in config: {channel_str}")
                except RPCError as e:
                    logger.error(f"Pyrogram RPCError while sending message to log channel {channel_str}: {e}")
                except Exception as e:
                    logger.error(f"Failed to send restart message to log channel {channel_str}: {e}")

        logger.info("Restart message handling attempted.")

    except FileNotFoundError:
        logger.error(f"Restart file {RESTART_FILE} not found.")
    except ValueError:
        logger.error(f"Invalid content in restart file {RESTART_FILE}: '{message_id_str}' is not a valid message ID.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in edit_restart_message: {e}")
    finally:
        # Ensure RESTART_FILE is deleted if it exists, after attempting to process
        if RESTART_FILE.exists():
            try:
                RESTART_FILE.unlink()
                logger.debug(f"Restart file {RESTART_FILE} deleted.")
            except OSError as e:
                logger.error(f"Error deleting restart file {RESTART_FILE}: {e}")


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
