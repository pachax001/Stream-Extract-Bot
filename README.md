# Streams Extractor Bot

A Telegram bot that extracts audio or subtitle streams from an uploaded video. Uses [WZGram](https://wzgram.com/) and FFmpeg.

## Deploy

Python 3.10 or newer is required. The supplied Dockerfile uses Debian Bookworm and Python 3.11.

1. Clone the repository and create the configuration:

   ```bash
   git clone https://github.com/rumalg123/Stream-Extract-Bot.git streamextract
   cd streamextract
   cp sample_config.env config.env
   ```

2. Set BOT_TOKEN, APP_ID, API_HASH, BOT_USERNAME, OWNER_ID and any permitted AUTH_USERS in config.env. Add the bot to logging channels when using the optional log IDs.

3. Start with Docker Compose:

   ```bash
   docker compose up --build -d
   ```

## Commands

- /start: Show the welcome message.
- /help and /about: Show existing bot information.
- Send a video file and press **DOWNLOAD and PROCESS**, then select an audio or subtitle stream.
- /status: Owner-only transfer and system status.
- /log: Owner-only log file.
- /restart: Owner-only restart. Attempts a Git update first, if this is a clean Git checkout; update failures are logged and the current installed code is restarted.

Normal startup **does not automatically reset your code** from an upstream repository. WZGram and PyroFork should not be installed together.

## Configuration

| Name | Meaning |
| --- | --- |
| BOT_TOKEN | Telegram bot token |
| APP_ID, API_HASH | Credentials from my.telegram.org |
| BOT_USERNAME | Bot username without @ |
| OWNER_ID | Telegram ID of owner |
| AUTH_USERS | Comma-separated permitted user IDs |
| LOG_CHANNEL | Optional extracted media log channel ID |
| LOG_MEDIA_CHANNEL | Optional original video log channel; defaults to LOG_CHANNEL |
| THRESHOLD | Free disk space reserved in GB (default 50) |
| MAX_DOWNLOAD_LIMIT | Concurrent downloads allowed per user (default 10) |
| UPSTREAM_REPO | Optional Git repository URL for /restart updates; defaults to this repository |
| UPSTREAM_BRANCH | Optional Git branch for /restart updates; defaults to main |

The bot cleans temporary downloads after processing or cancellation. Cancelled stream selections and failed extractions require the original video to be sent again.

Install without Docker using Python 3.10+ with `pip install -r requirements.txt`, and ensure FFmpeg and ffprobe are available in PATH.
