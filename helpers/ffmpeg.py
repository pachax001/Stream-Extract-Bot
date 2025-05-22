from pathlib import Path
from typing import Any, Dict, Callable

from pyrogram import Client
from pyrogram.types import Message

from helpers.logger import logger
from helpers.tools import execute, clean_up
from helpers.upload import upload_audio, upload_subtitle


async def _run_ffmpeg(
    cmd: list[str],
    filename: str
) -> bool:
    try:
        out, err, code, _ = await execute(cmd)
        if code != 0:
            logger.error(f"FFmpeg failed for {filename}: {err}")
            return False
        return True
    except Exception:
        logger.exception(f"Error running FFmpeg for {filename}")
        return False


async def _extract_and_upload(
    client: Client,
    message: Message,
    data: Dict[str, Any],
    file_ext: str,
    upload_fn: Callable[..., Any]
) -> None:
    """
    Generic helper to extract a stream and upload it.

    - file_ext: 'mp3' for audio, 'srt' for subtitle.
    - upload_fn: upload_audio or upload_subtitle.
    """
    filename = data.get("file_name", "<unknown>")
    user_id = data.get("user_id")
    user_name = data.get("user_first_name", "<unknown>")
    stream_map = data.get("map")
    source = data.get("file") or data.get("location")

    if not all([user_id, stream_map is not None, source]):
        await message.edit_text("❌ Extraction parameters missing. Aborting.")
        return

    source_path = Path(source)
    output_path = source_path.with_suffix(f".{file_ext}")

    logger.info(f"User {user_id}:{user_name} extracting {file_ext} (stream {stream_map}) from {filename}")
    await message.edit_text(f"⏳ Extracting {file_ext.upper()} from **{filename}**…")

    # Build FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", str(source_path),
        "-map", f"0:{stream_map}",
    ]

    if file_ext == "mp3":
        # Re-encode audio to MP3
        cmd += ["-c:a", "libmp3lame", "-b:a", "192k"]
    else:
        # Copy subtitles directly
        cmd += ["-c", "copy"]

    cmd.append(str(output_path))

    # Execute FFmpeg
    success = await _run_ffmpeg(cmd, filename)
    if not success:
        await clean_up(str(output_path))
        await message.edit_text(f"❌ Failed to extract **{file_ext}** from **{filename}**.")
        return

    # Cleanup source and upload
    await clean_up(str(source_path))
    await upload_fn(
        client, message,
        file_loc=str(output_path),
        username=user_name,
        user_id=user_id,
        file_name=filename
    )


async def extract_audio(
    client: Client,
    message: Message,
    data: Dict[str, Any]
) -> None:
    """
    Extracts the selected audio stream as MP3 and uploads it.
    """
    await _extract_and_upload(
        client, message, data,
        file_ext="mp3",
        upload_fn=upload_audio
    )


async def extract_subtitle(
    client: Client,
    message: Message,
    data: Dict[str, Any]
) -> None:
    """
    Extracts the selected subtitle stream as SRT and uploads it.
    """
    await _extract_and_upload(
        client, message, data,
        file_ext="srt",
        upload_fn=upload_subtitle
    )
