# status_updater.py

import asyncio
from pyrogram.errors import MessageNotModified, FloodWait, MessageIdInvalid
from utils.status_utils import get_status_text
from helpers.progress import ACTIVE_DOWNLOADS, ACTIVE_UPLOADS
from helpers.logger import logger

async def keep_updating_status(client, chat_id, message_id, stop_event=None):
    """
    Periodically updates the given message_id in chat_id with get_status_text() every 10 seconds.
    If stop_event is provided, it can be used to stop the loop externally.
    """
    while True:
        # Check if we have an external stop condition
        if stop_event and stop_event.is_set():
            break

        if not ACTIVE_DOWNLOADS and not ACTIVE_UPLOADS:
            try:
                await client.delete_messages(chat_id, message_id)
            except MessageIdInvalid:
                pass  # message may already have been deleted
            break

        try:
            new_text = get_status_text()
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=new_text
            )
        except MessageNotModified:
            # The text is the same as before; ignore it
            pass
        except FloodWait as e:
            # If Telegram rate-limits us, we must sleep
            await asyncio.sleep(e.value)
        except (MessageIdInvalid, RuntimeError):
            # The message might have been deleted or is no longer valid
            break
        except Exception as e:
            # Catch other unexpected exceptions and log or break
            logger.error("Error in status updater", exc_info=True)
            break

        # Wait 10 seconds before next update
        await asyncio.sleep(10)

    # Optionally do a final cleanup or log something here
    logger.info("Status updater loop ended")
