"""Update the running bot's Git checkout from the configured repo and branch.

Used on initial startup and by the owner-only /restart command.
"""
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from helpers.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / "config.env", override=True)

UPSTREAM_REPO = (os.getenv("UPSTREAM_REPO") or "").strip() or "https://github.com/rumalg123/Stream-Extract-Bot.git"
UPSTREAM_BRANCH = (os.getenv("UPSTREAM_BRANCH") or "").strip() or "main"


def _git(*args: str, timeout: int = 180) -> str:
    """Run Git without a shell or interactive password prompts."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
        env=env,
    )
    return result.stdout.strip()


def update_repository(repo: str, branch: str) -> bool:
    """Update to exactly the configured ref, including tracked local modifications.

    This intentionally replaces tracked files, like the former auto-updater,
    but never deletes .git, changes global Git config, or removes untracked
    config.env. Failure leaves the currently installed code available.
    """
    if not (PROJECT_ROOT / ".git").exists():
        logger.error("Automatic update skipped: %s is not a Git checkout", PROJECT_ROOT)
        return False
    if not repo.strip() or not branch.strip():
        logger.error("Automatic update skipped: UPSTREAM_REPO/UPSTREAM_BRANCH is empty")
        return False

    try:
        _git("check-ref-format", "--branch", branch)
        before = _git("rev-parse", "HEAD")
        # Fetch only the selected branch from the explicitly configured repo.
        _git("fetch", "--no-tags", repo, f"refs/heads/{branch}")
        target = _git("rev-parse", "FETCH_HEAD")
        _git("reset", "--hard", "FETCH_HEAD")
        if before == target:
            logger.info("Bot code already up to date: repo=%s branch=%s sha=%s", repo, branch, target[:12])
        else:
            logger.info(
                "Bot code updated: repo=%s branch=%s previous=%s current=%s",
                repo, branch, before[:12], target[:12],
            )
        return True
    except subprocess.CalledProcessError as exc:
        logger.error(
            "Automatic Git update failed (repo=%s branch=%s command=%r exit=%s): %s",
            repo, branch, exc.cmd, exc.returncode,
            (exc.stderr or exc.stdout or str(exc)).strip(),
            exc_info=True,
        )
    except subprocess.TimeoutExpired:
        logger.exception("Automatic Git update timed out (repo=%s branch=%s)", repo, branch)
    except OSError:
        logger.exception("Unable to run Git auto-update (repo=%s branch=%s)", repo, branch)
    return False


if __name__ == "__main__":
    if not update_repository(UPSTREAM_REPO, UPSTREAM_BRANCH):
        raise SystemExit(1)
