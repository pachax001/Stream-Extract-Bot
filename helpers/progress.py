import time
from typing import Any, Dict

from helpers.logger import logger

# Progress tracking registries
download_progress: Dict[str, Dict[str, Any]] = {}
callback_progress: Dict[str, Dict[str, Any]] = {}
upload_progress: Dict[str, Dict[str, Any]] = {}


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
    seconds, ms = divmod(int(ms), 1000)
    minutes, sec = divmod(seconds, 60)
    hours, min_ = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if min_:
        parts.append(f"{min_}m")
    if sec:
        parts.append(f"{sec}s")
    if ms:
        parts.append(f"{ms}ms")
    return ", ".join(parts) or "0s"


async def progress_func(
    current: float,
    total: float,
    ud_type: str,
    message: Any,
    start_time: float,
    original_message: Any,
    interval: float = 5.0,
) -> None:
    """
    Update global progress dictionaries at most every `interval` seconds or when complete.

    Args:
        current: Bytes processed so far.
        total: Total bytes to process.
        ud_type: "download" or "upload".
        message: Current Telegram message object.
        start_time: Epoch timestamp when transfer started.
        original_message: The original Telegram message object.
        interval: Minimum seconds between updates.
    """
    now = time.monotonic()
    elapsed = now - start_time
    if elapsed < 0:
        elapsed = 0

    # Only update if at least `interval` seconds have passed or transfer is done
    if elapsed < interval and current < total:
        return

    # Prevent division by zero
    speed = current / elapsed if elapsed > 0 else 0
    progress_pct = (current / total * 100) if total > 0 else 0

    elapsed_ms = elapsed * 1000
    eta_ms = ((total - current) / speed * 1000) if speed > 0 else 0

    record = {
        "file_name": original_message.document.file_name if ud_type == "dl" and original_message.document else "<unknown>",
        "ud_type": ud_type,
        "current": human_readable_bytes(current),
        "total": human_readable_bytes(total),
        "speed": f"{human_readable_bytes(speed)}/s",
        "progress": round(progress_pct, 2),
        "elapsed": format_duration(elapsed_ms),
        "eta": format_duration(eta_ms),
    }

    key = f"{original_message.chat.id}_{original_message.id}_{ud_type}"
    download_progress[key] = record

    callback_key = f"{message.chat.id}_{message.id}_callback"
    callback_progress[callback_key] = record

    #logger.info(f"[progress] {ud_type} {progress_pct:.2f}% ({key})")
