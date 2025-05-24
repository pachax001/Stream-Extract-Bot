from pathlib import Path
from typing import Any, Dict, Callable

from pyrogram import Client
from pyrogram.types import Message

from helpers.logger import logger
from helpers.tools import execute, clean_up
from helpers.upload import upload_audio, upload_subtitle
from helpers.progress import download_progress # Added for stream_info_key cleanup


async def _run_ffmpeg(
    cmd: list[str],
    filename: str # Original filename for logging
) -> bool:
    try:
        # Ensure all elements in cmd are strings
        cmd_str = [str(c) for c in cmd]
        logger.debug(f"Running FFmpeg command: {' '.join(cmd_str)}")
        out, err, code, _ = await execute(cmd_str)
        if code != 0:
            logger.error(f"FFmpeg failed for {filename}. Code: {code}\nError: {err}\nOutput: {out}")
            return False
        logger.info(f"FFmpeg successfully processed {filename}.")
        return True
    except Exception as e:
        logger.exception(f"Exception during FFmpeg execution for {filename}: {e}")
        return False


async def _extract_and_upload(
    client: Client,
    message: Message, # CallbackQuery's message, used for editing status
    data: Dict[str, Any], # Specific stream entry from download_progress[stream_info_key][idx_s]
    file_ext: str,
    upload_fn: Callable[..., Any],
    stream_info_key: str # Key for the parent dict in download_progress
) -> None:
    """
    Generic helper to extract a stream and upload it.
    Cleans up the main downloaded file and its entry in download_progress upon successful extraction.

    - data: The specific stream's dictionary (e.g., download_progress[stream_info_key][idx_s]).
    - file_ext: 'mp3' for audio, 'srt' for subtitle.
    - upload_fn: upload_audio or upload_subtitle.
    - stream_info_key: The key for the parent dictionary in download_progress, used for cleanup.
    """
    # 'file_name' in data here is the original file's name, used for the output file's base name.
    # 'source_file_display_name' is a more descriptive name for logging/messages.
    source_file_display_name = data.get("source_file_display_name", "<unknown_original_file>")
    
    user_id = data.get("user_id") # Should be populated by handle_extraction_callback
    user_name = data.get("user_first_name", "<unknown_user>")
    stream_map = data.get("map")
    
    # 'file_path' in data is the path to the master downloaded file (the source for ffmpeg)
    source_ffmpeg_path_str = data.get("file_path") 

    if not all([user_id is not None, stream_map is not None, source_ffmpeg_path_str]):
        logger.error(f"Extraction parameters missing for stream_info_key '{stream_info_key}'. Data: {data}")
        await message.edit_text("❌ **Error:** Essential extraction parameters are missing. Aborting.")
        return

    source_ffmpeg_path = Path(source_ffmpeg_path_str)
    if not source_ffmpeg_path.exists():
        logger.error(f"Source file for ffmpeg '{source_ffmpeg_path}' not found for stream_info_key '{stream_info_key}'.")
        await message.edit_text(f"❌ **Error:** Source file for extraction (`{source_ffmpeg_path.name}`) is missing. Aborting.")
        # No cleanup of download_progress here as the file is already gone.
        return

    # Construct a unique output file name based on original name + stream type + stream index
    # data['original_file_name_for_output'] should be the name of the originally downloaded file.
    base_output_name = Path(data.get("original_file_name_for_output", source_file_display_name)).stem
    output_file_name_constructor = f"{base_output_name}_stream_{stream_map}.{file_ext}"
    output_path = source_ffmpeg_path.with_name(output_file_name_constructor)


    logger.info(f"User {user_id}:{user_name} extracting {file_ext.upper()} (stream map {stream_map}) from '{source_file_display_name}' (key: {stream_info_key}) to '{output_path}'.")
    await message.edit_text(f"⏳ Extracting {file_ext.upper()} from **{source_file_display_name}** (stream {stream_map})…")
    
    codec_name = data.get("codec_name", "").lower() # 'codec_name' of the stream being extracted
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(source_ffmpeg_path),
        "-map", f"0:{stream_map}", # map specific stream
    ]

    # Codec selection logic
    if file_ext == "mp3": # Target is MP3 audio
        if codec_name == "mp3":
            cmd.extend(["-c:a", "copy"]) # Copy if already MP3
        else:
            cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"]) # Re-encode to MP3, -q:a 2 is VBR ~190kbps
    elif file_ext == "srt": # Target is SRT subtitle
        # For subtitles, -c:s copy is usually what you want if the format is already srt/ass/etc.
        # If it's a bitmap sub (e.g. dvdsub, pgs), it needs OCR, which ffmpeg doesn't do.
        # Assuming text-based subs for now.
        cmd.extend(["-c:s", "copy"]) # Copy subtitle stream
    else: # Other stream types
        cmd.extend(["-c", "copy"]) # Default to copy

    cmd.append(str(output_path))

    success = await _run_ffmpeg(cmd, source_file_display_name)
    if not success:
        await clean_up(str(output_path)) # Clean up potentially incomplete output file
        await message.edit_text(f"❌ Failed to extract **{file_ext.upper()}** (stream {stream_map}) from **{source_file_display_name}**.")
        # Do not clean up source_ffmpeg_path or download_progress[stream_info_key] here,
        # as user might want to retry or try another stream.
        return

    # --- Successful extraction ---
    
    # Upload the extracted file
    await upload_fn(
        client=client, 
        message=message, # Pass the CallbackQuery's message for upload status updates
        file_loc=str(output_path), # Path to the extracted file
        username=user_name,
        user_id=user_id,
        file_name=output_path.name # Use the actual name of the extracted file for upload
    )
    # upload_fn will delete output_path upon its own completion/failure.

    # After successful extraction AND upload (upload_fn is awaitable and its completion implies success or handled failure)
    # It's debatable whether source file cleanup should happen if upload fails.
    # Current helpers.upload structure suggests upload_fn handles its own output file cleanup.
    # We proceed to clean up the master source file IF this specific extraction was successful.

    logger.info(f"Successfully extracted {output_path.name}. Now cleaning up master source file: {source_ffmpeg_path_str}")
    await clean_up(str(source_ffmpeg_path)) # Delete the large source file

    if stream_info_key:
        # Check if all streams from this source file have been processed or if this is the last one.
        # This is complex. For now, we'll remove the entire stream_info_key entry
        # assuming one successful extraction implies the user is done with this source file.
        # A more advanced system might track individual stream states.
        if download_progress.pop(stream_info_key, None):
            logger.info(f"Cleaned up stream_info_key '{stream_info_key}' from download_progress after successful extraction and source file deletion.")
        else:
            logger.warning(f"Attempted to clean up stream_info_key '{stream_info_key}', but it was not found in download_progress.")


async def extract_audio(
    client: Client,
    message: Message,
    data: Dict[str, Any], # Specific stream's data from download_progress[stream_info_key][idx_s]
    stream_info_key: str  # Key for download_progress parent dict
) -> None:
    """
    Extracts the selected audio stream as MP3 and uploads it.
    `data` should contain info about the specific audio stream.
    `stream_info_key` is the key to the main downloaded file's info in `download_progress`.
    """
    await _extract_and_upload(
        client=client, 
        message=message, 
        data=data,
        file_ext="mp3",
        upload_fn=upload_audio,
        stream_info_key=stream_info_key
    )


async def extract_subtitle(
    client: Client,
    message: Message,
    data: Dict[str, Any], # Specific stream's data from download_progress[stream_info_key][idx_s]
    stream_info_key: str  # Key for download_progress parent dict
) -> None:
    """
    Extracts the selected subtitle stream (e.g., as SRT) and uploads it.
    `data` should contain info about the specific subtitle stream.
    `stream_info_key` is the key to the main downloaded file's info in `download_progress`.
    """
    # Determine appropriate extension based on subtitle codec if possible, default to 'srt'
    # For simplicity, always using 'srt'. FFmpeg will copy the stream as is.
    # If it's a format like ASS, it will be an SRT file containing ASS data, or ffmpeg might convert.
    # This might need refinement based on observed ffmpeg behavior with various subtitle codecs.
    file_ext = "srt" 
    # codec_name = data.get("codec_name", "").lower()
    # if codec_name == "ass":
    #     file_ext = "ass"
    # elif codec_name == "subrip":
    #     file_ext = "srt"
    # ... etc.

    await _extract_and_upload(
        client=client, 
        message=message, 
        data=data,
        file_ext=file_ext, # Use determined extension
        upload_fn=upload_subtitle,
        stream_info_key=stream_info_key
    )
