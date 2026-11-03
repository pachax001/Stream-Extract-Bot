import time
from typing import Any, Dict, Union

from pyrogram.types import Message # For type hinting original_message

from helpers.logger import logger

# Progress tracking registries
download_progress: Dict[str, Dict[str, Any]] = {}
upload_progress: Dict[str, Dict[str, Any]] = {} # Added for clarity, though it's the same structure
callback_progress: Dict[str, Dict[str, Any]] = {}


def human_readable_bytes(size: float) -> str:
    """
    Convert a byte count into a human-readable string (e.g., "1.23 MB").
    """
    if size <= 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.2f} {units[index]}"


def format_duration(ms: float) -> str:
    """
    Format milliseconds into a string like "1h, 23m, 45s".
    """
    seconds, ms_rem = divmod(int(ms), 1000) # Renamed ms to ms_rem to avoid conflict
    minutes, sec = divmod(seconds, 60)
    hours, min_ = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if min_:
        parts.append(f"{min_}m")
    if sec:
        parts.append(f"{sec}s")
    # Only show ms if duration is less than a second, for brevity
    if not parts and ms_rem:
        parts.append(f"{ms_rem}ms")
    return ", ".join(parts) or "0s"


async def progress_func(
    current: float,
    total: float,
    ud_type: str, # "dl" for download, "ul" for upload
    status_message: Message, # The message being updated with progress (status_msg)
    start_time: float,
    original_message: Message, # The message that initiated the operation
                               # For downloads, it's the message with media.
                               # For uploads, it's the callback query's message.
    file_name_display: str = "<unknown>", # Pass filename explicitly for uploads
    interval: float = 3.0, # Standardized interval
    last_update_time: Dict[str, float] = None # To manage update frequency per task
) -> None:
    """
    Update global progress dictionaries at most every `interval` seconds or when complete.

    Args:
        current: Bytes processed so far.
        total: Total bytes to process.
        ud_type: "dl" or "ul".
        status_message: Current Telegram message object being updated with progress.
        start_time: Epoch timestamp when transfer started.
        original_message: The original Telegram message object that triggered the action.
        file_name_display: The name of the file being processed.
        interval: Minimum seconds between updates.
        last_update_time: A dictionary to store the last update time for the current task.
                          Pass an empty dict for the first call of a task.
    """
    now = time.monotonic()
    
    # Key for managing last update time for this specific task
    task_progress_key = f"{original_message.chat.id}_{original_message.id}_{ud_type}"

    if last_update_time is None: # Should ideally be initialized by the caller for each new task
        last_update_time = {}
    
    if current < total and (now - last_update_time.get(task_progress_key, 0)) < interval:
        return
    
    last_update_time[task_progress_key] = now

    elapsed = now - start_time
    if elapsed < 0: # Should not happen with monotonic time
        elapsed = 0

    speed = current / elapsed if elapsed > 0 else 0
    progress_pct = (current / total * 100) if total > 0 else 0
    
    # For downloads, original_message.document might exist. For uploads, it won't.
    actual_file_name = file_name_display
    if ud_type == "dl" and original_message.document and original_message.document.file_name:
        actual_file_name = original_message.document.file_name
    elif ud_type == "dl" and original_message.video and original_message.video.file_name:
        actual_file_name = original_message.video.file_name
    elif ud_type == "dl" and original_message.audio and original_message.audio.file_name:
        actual_file_name = original_message.audio.file_name


    record = {
        "file_name": actual_file_name,
        "ud_type": ud_type,
        "current": human_readable_bytes(current),
        "total": human_readable_bytes(total),
        "speed": f"{human_readable_bytes(speed)}/s",
        "progress": round(progress_pct, 2),
        "elapsed": format_duration(elapsed * 1000),
        "eta": format_duration(((total - current) / speed * 1000) if speed > 0 else 0),
        "status_msg_id": status_message.id,
        "status_msg_chat_id": status_message.chat.id,
        "original_msg_id": original_message.id,
        "original_msg_chat_id": original_message.chat.id,
        "start_time": start_time, # Store start_time for potential resume/recalculations
    }

    # Main progress key for dl/ul operations, based on the message that initiated it
    main_progress_key = task_progress_key # Same as task_progress_key

    if ud_type == "dl":
        download_progress[main_progress_key] = record
    elif ud_type == "ul":
        upload_progress[main_progress_key] = record
    else:
        logger.warning(f"Unknown ud_type: {ud_type} in progress_func")
        return

    # Callback progress key is based on the status_message (the one with the button)
    # This is used by the callback query handler to show detailed progress on alert
    callback_key = f"{status_message.chat.id}_{status_message.id}_callback"
    callback_progress[callback_key] = record
    
    # logger.debug(f"Progress: {ud_type} {actual_file_name} - {progress_pct:.2f}% ID: {main_progress_key}")
    # logger.debug(f"Callback Progress for {callback_key} updated.")

# Example of how last_update_time should be managed by caller:
# my_task_last_update = {} # Initialize once per new download/upload task
# await actual_pyrogram_downloader_or_uploader(
#    progress=progress_func,
#    progress_args=(
#        "dl_or_ul", 
#        status_msg_obj, 
#        time.monotonic(), 
#        original_msg_obj,
#        "my_file.mkv", 
#        3.0, # interval
#        my_task_last_update # pass the dict here
#    )
# )
