import os
from dotenv import load_dotenv
from helpers.logger import logger

# Load environment variables from .env file
load_dotenv('config.env')

class Config(object):
    # Get a bot token from botfather
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    # Get from my.telegram.org (or @UseTGXBot)
    APP_ID = int(os.environ.get("APP_ID"))  # Default value 0 if not provided
    API_HASH = os.environ.get("API_HASH")

    # Owner ID is required, so we raise an error if it's missing or not an integer
    OWNER_ID = os.environ.get("OWNER_ID")
    if OWNER_ID is None:
        raise ValueError("OWNER_ID environment variable is missing.")
    try:
        OWNER_ID = int(OWNER_ID)
    except ValueError:
        raise ValueError("OWNER_ID must be an integer.")

    # AUTH_USERS, LOG_CHANNEL, and BOT_USERNAME are optional
    AUTH_USERS = set(int(x) for x in os.environ.get("AUTH_USERS", "").split(',')) if os.environ.get("AUTH_USERS") else set()
    LOG_CHANNEL = os.environ.get("LOG_CHANNEL")
    LOG_MEDIA_CHANNEL = os.environ.get("LOG_MEDIA_CHANNEL")
    BOT_USERNAME = os.environ.get("BOT_USERNAME")
    THRESHOLD = int(os.environ.get("THRESHOLD", 50))
    MAX_DOWLOAD_LIMIT = int(os.environ.get("MAX_DOWLOAD_LIMIT", 5))

    if LOG_CHANNEL is None or LOG_CHANNEL == "":
        logger.info("LOG_CHANNEL environment variable is missing. Messages will not be logged.")
    else:
        if LOG_MEDIA_CHANNEL is None or LOG_MEDIA_CHANNEL == "":
            logger.info("LOG_MEDIA_CHANNEL environment variable is missing. LOG_CHANNEL will be used for logging media messages.")

        

    # Check if required environment variables are missing
    MISSING_VARIABLES = [var for var in ["BOT_TOKEN", "APP_ID", "API_HASH",  "BOT_USERNAME", "OWNER_ID","THRESHOLD"] if os.environ.get(var) is None or os.environ.get(var) == ""]
    if MISSING_VARIABLES:
        raise ValueError(f"The following required environment variables are missing: {', '.join(MISSING_VARIABLES)}")
