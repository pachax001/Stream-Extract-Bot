"""Read and validate the existing bot environment variables."""
import os
from typing import Any

from dotenv import load_dotenv
from helpers.logger import logger

load_dotenv("config.env")


def _get_env(
    name: str, *, default: str | None = None,
    required: bool = False, cast: type | None = None,
) -> Any:
    raw = os.getenv(name)
    # Blank optional values in sample_config.env should use their defaults.
    if raw is None or not raw.strip():
        if required:
            raise ValueError(f"Missing required environment variable: {name}")
        raw = default
    if cast is not None and raw is not None:
        try:
            return cast(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Environment variable {name} must be a {cast.__name__}"
            ) from exc
    return raw


class Config:
    MOUNT_POINT = "/"
    BOT_TOKEN = _get_env("BOT_TOKEN", required=True)
    APP_ID = _get_env("APP_ID", required=True, cast=int)
    API_HASH = _get_env("API_HASH", required=True)
    BOT_USERNAME = _get_env("BOT_USERNAME", required=True).lstrip("@")
    OWNER_ID = _get_env("OWNER_ID", required=True, cast=int)

    AUTH_USERS = {
        int(user.strip())
        for user in (_get_env("AUTH_USERS", default="") or "").split(",")
        if user.strip()
    }
    LOG_CHANNEL = _get_env("LOG_CHANNEL")
    LOG_MEDIA_CHANNEL = _get_env("LOG_MEDIA_CHANNEL") or LOG_CHANNEL

    THRESHOLD = _get_env("THRESHOLD", cast=int, default="50")
    MAX_DOWNLOAD_LIMIT = _get_env("MAX_DOWNLOAD_LIMIT", cast=int, default="10")
    if THRESHOLD < 0:
        raise ValueError("THRESHOLD must be zero or greater")
    if MAX_DOWNLOAD_LIMIT < 1:
        raise ValueError("MAX_DOWNLOAD_LIMIT must be at least 1")

    if not LOG_CHANNEL:
        logger.info("LOG_CHANNEL is not set; extracted file logging is disabled.")
    elif not _get_env("LOG_MEDIA_CHANNEL"):
        logger.info("LOG_MEDIA_CHANNEL is not set; source media uses LOG_CHANNEL.")
