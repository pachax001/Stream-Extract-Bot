import asyncio
from pyrogram import Client
from pyrogram.errors import MessageNotModified, FloodWait, MessageIdInvalid

from helpers.logger import logger
from utils.status_utils import get_status_text
from helpers.progress import download_progress, upload_progress


def keep_updating_status(
    client: Client,
    chat_id: int,
    message_id: int,
    stop_event: asyncio.Event | None = None,
    interval: float = 10.0
) -> asyncio.Task:
    """
    Start a background task that updates the given message every `interval` seconds
    with the current status. If no transfers are active, the message is deleted
    and the loop ends.

    Returns an asyncio.Task which can be cancelled to stop updates early.
    """
    async def _updater() -> None:
        while True:
            if not download_progress and not upload_progress:
                await client.delete_messages(chat_id, message_id)
                break

            # External stop condition
            if stop_event and stop_event.is_set():
                break

            # If no active transfers, delete message and exit
            if not download_progress and not upload_progress:
                try:
                    await client.delete_messages(chat_id, message_id)
                except (MessageIdInvalid, Exception):
                    pass
                break

            try:
                new_text = get_status_text()
                await client.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=new_text
                )
            except MessageNotModified:
                # no change in text
                pass
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except (MessageIdInvalid, RuntimeError):
                # message gone or invalid
                break
            except Exception as e:
                logger.error("Error in status updater", exc_info=True)
                break

            await asyncio.sleep(interval)

        logger.info("Status updater loop ended")

    # Schedule the updater task
    return asyncio.create_task(_updater())