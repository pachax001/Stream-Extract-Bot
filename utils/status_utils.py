import shutil
import psutil
from pathlib import Path
from typing import Any, Dict, List

from helpers.progress import download_progress, upload_progress
from helpers.logger import logger


def _format_transfer_section(
    title: str,
    progress_registry: Dict[str, Dict[str, Any]]
) -> List[str]:
    """
    Format a section showing ongoing transfers (downloads or uploads) from a progress registry.
    """
    lines: List[str] = [f"**{title}**:"]
    for uid, info in progress_registry.items():
        name = info.get("file_name", "UnknownFile")
        current = info.get("current", "0 B")
        total = info.get("total", "0 B")
        pct = info.get("progress", 0.0)
        speed = info.get("speed", "N/A")
        eta = info.get("eta", "N/A")

        lines.append(
            f"• **{name}**  `[{current}/{total}]` ({pct:.2f}%)  "
            f"Speed: {speed}  ETA: {eta}"
        )
    lines.append("")  # blank line for spacing
    return lines


def get_status_text(mount_point: str = "/") -> str:
    """
    Returns a multi-line status report including:
      - Ongoing downloads
      - Ongoing uploads
      - Disk usage on `mount_point`
      - CPU & RAM utilization
    """
    lines: List[str] = []

    # Downloads
    if download_progress:
        logger.info("Reporting active downloads")
        lines.extend(_format_transfer_section("Ongoing Downloads", download_progress))
    else:
        lines.append("**No downloads in progress.**\n")

    # Uploads
    if upload_progress:
        logger.info("Reporting active uploads")
        lines.extend(_format_transfer_section("Ongoing Uploads", upload_progress))
    else:
        lines.append("**No uploads in progress.**\n")

    # Disk usage
    try:
        total, used, free = shutil.disk_usage(mount_point)
        total_gb, used_gb, free_gb = (v / (1024**3) for v in (total, used, free))
        lines.extend([
            "**Disk Usage**:",
            f"• Total: `{total_gb:.2f} GB`",
            f"• Used:  `{used_gb:.2f} GB`",
            f"• Free:  `{free_gb:.2f} GB`",
            ""
        ])
    except Exception as e:
        logger.error(f"Failed to get disk usage for {mount_point}: {e}")
        lines.append("**Disk Usage**: unavailable\n")

    # CPU & RAM
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        lines.extend([
            "**System Usage**:",
            f"• CPU Usage: `{cpu:.1f}%`",
            f"• RAM Usage: `{ram:.1f}%`"
        ])
    except Exception as e:
        logger.error(f"Failed to get system usage: {e}")
        lines.append("**System Usage**: unavailable")

    return "\n".join(lines)
