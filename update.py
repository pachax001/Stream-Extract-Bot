import os
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from helpers.logger import logger

# Load environment variables
env_path = Path("config.env")
if env_path.exists():
    load_dotenv(env_path, override=True)

# Configuration
UPSTREAM_REPO = os.getenv(
    "UPSTREAM_REPO",
    "https://github.com/pachax001/Stream-Extract-Bot"
)
UPSTREAM_BRANCH = os.getenv("UPSTREAM_BRANCH", "main")

# File paths
LOG_FILE = Path("log.txt")
GIT_DIR = Path(".git")


def clear_log_file() -> None:
    """
    Truncate the log file if it exists.
    """
    try:
        if LOG_FILE.exists():
            LOG_FILE.write_text("")
            logger.info(f"Cleared log file: {LOG_FILE}")
    except Exception as e:
        logger.error(f"Failed to clear log file: {e}")


def update_repository(repo: str, branch: str) -> bool:
    """
    Reinitialize git and reset to the specified upstream repository and branch.

    Returns True on success, False on failure.
    """
    try:
        # Remove existing git metadata
        if GIT_DIR.exists():
            shutil.rmtree(GIT_DIR)
            logger.info("Removed existing .git directory.")

        # Initialize new repo and configure
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(
            ["git", "config", "--global", "user.email", "pachax001@gmail.com"],
            check=True
        )
        subprocess.run(
            ["git", "config", "--global", "user.name", "pachax001"],
            check=True
        )

        # Commit current state
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(
            ["git", "commit", "-sm", "update", "-q"],
            check=True
        )

        # Link to upstream and hard reset
        subprocess.run(
            ["git", "remote", "add", "origin", repo],
            check=True
        )
        subprocess.run(["git", "fetch", "origin", "-q"], check=True)
        subprocess.run(
            ["git", "reset", "--hard", f"origin/{branch}", "-q"],
            check=True
        )
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to update repository: {e}")
        return False


def main() -> None:
    """
    Clear logs and perform the repository update.
    """
    clear_log_file()

    if not UPSTREAM_REPO:
        logger.error("UPSTREAM_REPO is not set; skipping update.")
        return

    success = update_repository(UPSTREAM_REPO, UPSTREAM_BRANCH)
    if success:
        logger.info("Successfully updated with latest commit from UPSTREAM_REPO")
    else:
        logger.error(
            "Something went wrong while updating. Verify that UPSTREAM_REPO and UPSTREAM_BRANCH are correct."
        )


if __name__ == "__main__":
    main()
