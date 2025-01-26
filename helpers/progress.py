import os
import time
import asyncio
from helpers.logger import logger

PRGRS = {}
PRGRS_CALLBACK = {}
ACTIVE_DOWNLOADS = {}
ACTIVE_UPLOADS = {} 
async def progress_func(
    current,
    total,
    ud_type,
    message,
    start,
    original_message,
):
    now = time.time()
    diff = now - start
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff * 1000)  # milliseconds
        time_to_completion = round((total - current) / speed * 1000)  # milliseconds
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time_str = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time_str = TimeFormatter(milliseconds=estimated_total_time)
        unique_id = f"{original_message.chat.id}_{original_message.id}_{ud_type}"
        unique_id_callback = f"{message.chat.id}_{message.id}_callback"
        logger.info(f"Progress for {unique_id}: {percentage}%")
        PRGRS[unique_id] = {
            "ud_type": ud_type,
            "current": humanbytes(current),
            "total": humanbytes(total),
            "speed": humanbytes(speed) + "/s",
            "progress": percentage,
            "elapsed": elapsed_time_str,
            "eta": estimated_total_time_str
        }
        PRGRS_CALLBACK[unique_id_callback] = {
            "ud_type": ud_type,
            "current": humanbytes(current),
            "total": humanbytes(total),
            "speed": humanbytes(speed) + "/s",
            "progress": percentage,
            "elapsed": elapsed_time_str,
            "eta": estimated_total_time_str
        }

def humanbytes(size):
    if not size:
        return ""
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp.rstrip(', ')
