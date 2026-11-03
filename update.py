"""Safely update the deployed checkout when the owner invokes /restart."""
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from helpers.logger import logger

load_dotenv("config.env", override=True)
UPSTREAM_REPO = os.getenv(
    "UPSTREAM_REPO", "https://github.com/rumalg123/Stream-Extract-Bot.git"
)
UPSTREAM_BRANCH = os.getenv("UPSTREAM_BRANCH", "main")


def update_repository(repo: str, branch: str) -> bool:
    """Update a clean Git checkout, without recreating .git or changing Git globals."""
    if not Path(".git").exists():
        logger.warning("Not a Git checkout; leaving installed files unchanged.")
        return False
    try:
        # Do not destroy tracked local modifications on a running deployment.
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, check=True,
        )
        if dirty.stdout.strip():
            logger.error("Working tree has local changes; skipping automatic update.")
            return False

        subprocess.run(
            ["git", "fetch", "--no-tags", repo, f"refs/heads/{branch}"],
            capture_output=True, text=True, check=True,
        )
        subprocess.run(
            ["git", "reset", "--hard", "FETCH_HEAD"],
            capture_output=True, text=True, check=True,
        )
        logger.info("Updated checkout from %s branch %s", repo, branch)
        return True
    except (OSError, subprocess.CalledProcessError):
        logger.exception("Could not update checkout from %s branch %s", repo, branch)
        return False


if __name__ == "__main__":
    if not update_repository(UPSTREAM_REPO, UPSTREAM_BRANCH):
        raise SystemExit(1)
