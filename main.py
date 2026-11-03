"""WZGram bot entry point and restart notifications."""
import asyncio
import datetime
from pathlib import Path

import pytz
from wzgram import Client
from wzgram.errors import RPCError

from helpers.logger import logger
from config import Config

RESTART_FILE = Path("restart_msg_id.txt")
VERSION = "v1.1.2.m"
TIMEZONE = pytz.timezone("Asia/Colombo")


async def edit_restart_message(app: Client) -> None:
    if not RESTART_FILE.exists():
        return

    try:
        message_id = int(RESTART_FILE.read_text(encoding="utf-8").strip())
        now = datetime.datetime.now(TIMEZONE)
        restart_text = (
            f"⌬ Restarted Successfully!\n"
            f"┠ Date: {now:%d/%m/%y}\n"
            f"┠ Time: {now:%I:%M:%S %p}\n"
            f"┠ TimeZone: {TIMEZONE.zone}\n"
            f"┖ Version: {VERSION}"
        )

        try:
            await app.edit_message_text(
                chat_id=Config.OWNER_ID, message_id=message_id, text=restart_text
            )
        except RPCError:
            logger.exception("Could not edit owner restart notification")

        for channel in {Config.LOG_CHANNEL, Config.LOG_MEDIA_CHANNEL}:
            if not channel:
                continue
            try:
                await app.send_message(chat_id=int(channel), text=restart_text)
            except (ValueError, RPCError):
                logger.exception("Could not send restart notification to channel %s", channel)
    except (ValueError, OSError):
        logger.exception("Invalid or inaccessible restart notification file")
    finally:
        try:
            RESTART_FILE.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not delete restart notification file")


async def main() -> None:
    app = Client(
        "TroJanz",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.APP_ID,
        api_hash=Config.API_HASH,
        plugins=dict(root="plugins"),
        workers=300,
        max_concurrent_transmissions=100,
    )
    started = False
    try:
        await app.start()
        started = True
        me = await app.get_me()
        logger.info("%s has started using WZGram", me.username)
        await edit_restart_message(app)
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Uncaught error in bot lifecycle")
        raise
    finally:
        if started:
            try:
                await app.stop()
            except Exception:
                logger.exception("Unable to stop WZGram client cleanly")


if __name__ == "__main__":
    logger.info("Starting bot...")
    asyncio.run(main())
