"""Update the owner's status message while transfers are active."""
import asyncio

from wzgram import Client
from wzgram.enums import ParseMode
from wzgram.errors import MessageNotModified, FloodWait, MessageIdInvalid, RPCError

from helpers.logger import logger
from utils.status_utils import get_status_text
from helpers.progress import download_progress, upload_progress


def keep_updating_status(
    client: Client,
    chat_id: int,
    message_id: int,
    stop_event: asyncio.Event | None = None,
    interval: float = 10.0,
) -> asyncio.Task:
    """Return an updater task that ends after transfers finish or status is removed."""

    async def _updater() -> None:
        try:
            while not (stop_event and stop_event.is_set()):
                if not download_progress and not upload_progress:
                    try:
                        await client.delete_messages(chat_id, message_id)
                    except RPCError:
                        logger.exception("Could not remove completed status message %s", message_id)
                    break
                try:
                    await client.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=get_status_text(),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except MessageNotModified:
                    pass
                except FloodWait as exc:
                    await asyncio.sleep(exc.value)
                    continue
                except MessageIdInvalid:
                    break
                except RPCError:
                    logger.exception("Could not update status message %s", message_id)
                    break
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Status updater stopped after unexpected error")
        finally:
            logger.debug("Status updater finished for message %s", message_id)

    return asyncio.create_task(_updater())
