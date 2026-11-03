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
- /restart: Owner-only **update and restart**. Fetches the configured repository and branch, then restarts the bot so the updated code loads. Update failures are logged and the installed code is restarted.

## Automatic updates

On **every startup**, `start.sh` first runs `update.py`, which fetches `UPSTREAM_REPO` and `UPSTREAM_BRANCH` from `config.env` and resets the local tracked files to that exact branch. The bot starts immediately afterward. If fetching fails, it logs the error and still starts the installed version.

The owner-only `/restart` command also runs `update.py` **before** restarting, so you can deploy new code without manually restarting the container.

For example, in `config.env`:

```env
UPSTREAM_REPO="https://github.com/rumalg123/Stream-Extract-Bot.git"
UPSTREAM_BRANCH="main"
```

**Important:** While testing the unmerged PR, set `UPSTREAM_BRANCH="fix/wzgram-robustness-20261103"` instead of `main`. Switch to `main` after merging.

The update mechanism requires the bot directory to be a **Git checkout with its `.git` metadata available**, including inside the Docker container. It intentionally discards local changes to *tracked* files to match your selected branch, but preserves the ignored `config.env` file. It does not recreate `.git`, change global Git settings, or delete untracked files. Updating source code does **not** install new dependencies; rebuild the Docker image if `requirements.txt` or system dependencies change.

WZGram and PyroFork should not be installed together.

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
| UPSTREAM_REPO | Git repository URL used by automatic startup updates and /restart; defaults to this repository |
| UPSTREAM_BRANCH | Git branch used by automatic startup updates and /restart; defaults to main |

The bot cleans temporary downloads after processing or cancellation. Cancelled stream selections and failed extractions require the original video to be sent again.

Install without Docker using Python 3.10+ with `pip install -r requirements.txt`, and ensure FFmpeg and ffprobe are available in PATH.
