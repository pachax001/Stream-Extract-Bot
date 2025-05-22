# config.py
import os
from dotenv import load_dotenv
from helpers.logger import logger

load_dotenv("config.env")

def _get_env(
    name: str,
    *,
    default: str | None = None,
    required: bool = False,
    cast: type | None = None,
) -> any:
    """
    Fetches and validates an environment variable.
    - required: if True, raises ValueError when missing or blank
    - cast: a type (e.g. int) to cast the value to
    """
    raw = os.getenv(name, default)
    if required and (raw is None or raw.strip() == ""):
        raise ValueError(f"Missing required environment variable: {name}")
    if cast and raw not in (None, ""):
        try:
            return cast(raw)
        except (TypeError, ValueError):
            raise ValueError(f"Env var {name} must be of type {cast.__name__}")
    return raw

class Config:
    MOUNT_POINT         = "/"
    BOT_TOKEN           = _get_env("BOT_TOKEN", required=True)
    APP_ID              = _get_env("APP_ID", required=True,  cast=int)
    API_HASH            = _get_env("API_HASH", required=True)
    BOT_USERNAME        = _get_env("BOT_USERNAME", required=True)
    OWNER_ID            = _get_env("OWNER_ID", required=True,  cast=int)

    # Optional envs
    AUTH_USERS          = {
                           int(u) for u in _get_env("AUTH_USERS", default="").split(",") if u.strip()
                         }
    LOG_CHANNEL         = _get_env("LOG_CHANNEL")
    LOG_MEDIA_CHANNEL   = _get_env("LOG_MEDIA_CHANNEL") or LOG_CHANNEL

    THRESHOLD           = _get_env("THRESHOLD", cast=int, default="50")
    MAX_DOWNLOAD_LIMIT  = _get_env("MAX_DOWNLOAD_LIMIT", cast=int, default="10")

    # Warnings for truly optional variables
    if not LOG_CHANNEL:
        logger.info("LOG_CHANNEL is not set; media logs will not be sent.")
    elif not os.getenv("LOG_MEDIA_CHANNEL"):
        logger.info("LOG_MEDIA_CHANNEL is not set; using LOG_CHANNEL for media.")

