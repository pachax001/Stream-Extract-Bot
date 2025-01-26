# status_utils.py

import shutil
import psutil
from helpers.progress import ACTIVE_DOWNLOADS, PRGRS, humanbytes, ACTIVE_UPLOADS

def get_status_text():
    """
    Builds a status string with:
      - Ongoing downloads from ACTIVE_DOWNLOADS/PRGRS
      - Disk usage
      - CPU/RAM usage (via psutil)
    """
    lines = []

    # 1) Ongoing downloads
    if not ACTIVE_DOWNLOADS:
        lines.append("**No downloads in progress.**\n")
    else:
        lines.append("**Ongoing Downloads**:")
        for unique_id, info in ACTIVE_DOWNLOADS.items():
            file_name = info.get("file_name", "UnknownFile")

            # Check if we have progress info for this unique_id
            if unique_id in PRGRS:
                prg = PRGRS[unique_id]
                current = prg["current"]
                total = prg["total"]
                pct = prg["progress"]
                speed = prg["speed"]
                eta = prg["eta"]
                lines.append(
                    f"• **{file_name}**\n"
                    f"  - Progress: {current}/{total} ({pct:.2f}%)\n"
                    f"  - Speed: {speed}\n"
                    f"  - ETA: {eta}\n"
                )
            else:
                # It's in ACTIVE_DOWNLOADS but not yet in PRGRS
                lines.append(f"• **{file_name}**\n  - Progress: Initializing...\n")
        lines.append("")
    
    if not ACTIVE_UPLOADS:
        lines.append("**No uploads in progress.**\n")
    else:
        lines.append("**Ongoing Uploads**:")
        for unique_id, info in ACTIVE_UPLOADS.items():
            file_name = info.get("file_name", "UnknownFile")

            # Check if we have progress info for this unique_id
            if unique_id in PRGRS:
                prg = PRGRS[unique_id]
                current = prg["current"]
                total = prg["total"]
                pct = prg["progress"]
                speed = prg["speed"]
                eta = prg["eta"]
                lines.append(
                    f"• **{file_name}**\n"
                    f"  - Progress: {current}/{total} ({pct:.2f}%)\n"
                    f"  - Speed: {speed}\n"
                    f"  - ETA: {eta}\n"
                )
            else:
                # It's in ACTIVE_DOWNLOADS but not yet in PRGRS
                lines.append(f"• **{file_name}**\n  - Progress: Initializing...\n")
        lines.append("")
    # 2) Disk usage
    total, used, free = shutil.disk_usage("/")
    total_gb = total / (1024**3)
    used_gb = used / (1024**3)
    free_gb = free / (1024**3)

    lines.append(
        f"**Disk Usage**:\n"
        f"• Total: `{total_gb:.2f} GB`\n"
        f"• Used:  `{used_gb:.2f} GB`\n"
        f"• Free:  `{free_gb:.2f} GB`\n"
    )

    # 3) CPU & RAM usage
    cpu_percent = psutil.cpu_percent(interval=0)
    ram_info = psutil.virtual_memory()
    lines.append(
        f"**System Usage**:\n"
        f"• CPU Usage: `{cpu_percent}%`\n"
        f"• RAM Usage: `{ram_info.percent}%`\n"
    )

    return "\n".join(lines)
