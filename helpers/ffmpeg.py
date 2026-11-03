"""Extract a selected audio or subtitle stream and upload the result."""
from pathlib import Path
from typing import Any, Callable, Awaitable

from wzgram import Client
from wzgram.types import Message

from helpers.logger import logger
from helpers.tools import execute, clean_up
from helpers.upload import upload_audio, upload_subtitle
from helpers.progress import download_progress


async def _extract_and_upload(
    client: Client,
    message: Message,
    data: dict[str, Any],
    file_ext: str,
    upload_fn: Callable[..., Awaitable[bool]],
    stream_info_key: str,
) -> bool:
    source_path_str = data.get("file_path")
    source_name = data.get("source_file_display_name") or data.get("file_name") or "video"
    index = data.get("map")
    user_id = data.get("user_id")
    user_name = data.get("user_first_name") or "User"

    if not source_path_str or not isinstance(index, int) or user_id is None:
        logger.error("Invalid extraction metadata for key=%s: %r", stream_info_key, data)
        await _safe_edit(message, "❌ Essential extraction parameters are missing.")
        return False

    source_path = Path(source_path_str)
    if not source_path.is_file():
        logger.error("Extraction source is missing: %s", source_path)
        download_progress.pop(stream_info_key, None)
        await _safe_edit(message, "❌ The source video is no longer available.")
        return False

    base_name = Path(data.get("original_file_name_for_output") or source_name).stem
    output_path = source_path.with_name(f"{base_name}_stream_{index}.{file_ext}")
    codec_name = str(data.get("codec_name") or "").lower()

    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-y", "-i", str(source_path), "-map", f"0:{index}"
    ]
    if file_ext == "mp3":
        if codec_name == "mp3":
            cmd.extend(["-c:a", "copy"])
        else:
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"])
    else:
        # Convert text subtitle codecs to genuine SRT instead of copying
        # ASS, MOV_TEXT, etc. into a file incorrectly named .srt.
        cmd.extend(["-c:s", "srt"])
    cmd.append(str(output_path))

    try:
        await _safe_edit(
            message, f"⏳ Extracting {file_ext.upper()} stream {index}..."
        )
        out, err, code, _ = await execute(cmd)
        if code != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
            logger.error(
                "FFmpeg extraction failed: key=%s stream=%s rc=%s stderr=%s stdout=%s",
                stream_info_key, index, code, err, out,
            )
            await _safe_edit(
                message, f"❌ Failed to extract {file_ext.upper()} stream {index}."
            )
            return False

        result = await upload_fn(
            client=client,
            message=message,
            file_loc=str(output_path),
            username=user_name,
            user_id=user_id,
            file_name=output_path.name,
        )
        if result:
            logger.info(
                "Extracted and uploaded %s stream=%s for user=%s",
                source_name, index, user_id,
            )
        return result
    except Exception:
        logger.exception(
            "Unexpected extraction failure for key=%s stream=%s", stream_info_key, index
        )
        await _safe_edit(message, "❌ Extracting or uploading the stream failed.")
        return False
    finally:
        # The selection message is consumed after one extraction; retaining files
        # on failure creates unreachable disk usage and exhausts the download disk.
        download_progress.pop(stream_info_key, None)
        await clean_up(output_path, source_path)
        if source_path.parent.name == str(source_path.parent.name) and source_path.parent.parent.name == "downloads":
            await clean_up(source_path.parent)


async def _safe_edit(message: Message, text: str) -> None:
    try:
        await message.edit_text(text)
    except Exception:
        logger.exception("Failed to update extraction status chat=%s message=%s", message.chat.id, message.id)


async def extract_audio(
    client: Client, message: Message, data: dict[str, Any], stream_info_key: str
) -> bool:
    return await _extract_and_upload(client, message, data, "mp3", upload_audio, stream_info_key)


async def extract_subtitle(
    client: Client, message: Message, data: dict[str, Any], stream_info_key: str
) -> bool:
    return await _extract_and_upload(client, message, data, "srt", upload_subtitle, stream_info_key)
