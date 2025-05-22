import asyncio
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Union, Sequence

from helpers.logger import logger


def _prepare_args(command: Union[str, Sequence[str]]) -> list[str]:
    """
    Prepare command arguments for subprocess execution, handling both string and sequence inputs.
    """
    if isinstance(command, str):
        return shlex.split(command)
    return list(command)


async def execute(
    command: Union[str, Sequence[str]],
    timeout: Optional[float] = None
) -> Tuple[str, str, int, int]:
    """
    Execute a shell command asynchronously.

    Args:
        command: Command to run (string or list of args).
        timeout: Seconds before forcibly terminating the process.

    Returns:
        stdout, stderr, return_code, pid
    """
    args = _prepare_args(command)
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            msg = f"[execute] Command timeout after {timeout}s"
            logger.error(msg)
            return "", msg, -1, proc.pid

        out = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()
        return out, err, proc.returncode, proc.pid

    except Exception as e:
        err_msg = f"[execute] Exception: {e}"
        logger.error(err_msg)
        return "", err_msg, -1, 0


async def clean_up(
    *paths: Union[str, Path],
    retries: int = 3,
    delay: float = 1.0
) -> None:
    """
    Attempt to delete each provided path (file or directory) up to `retries` times,
    waiting `delay` seconds between attempts.

    Args:
        paths: Paths to delete.
        retries: Maximum deletion attempts per path.
        delay: Delay between retries in seconds.
    """
    for raw in paths:
        path = Path(raw)
        for attempt in range(1, retries + 1):
            if not path.exists():
                logger.info(f"[clean_up] {path!r} not found; skipping.")
                break
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    logger.info(f"[clean_up] Removed directory {path!r} (attempt {attempt}).")
                else:
                    path.unlink()
                    logger.info(f"[clean_up] Deleted file {path!r} (attempt {attempt}).")
                break
            except Exception as e:
                logger.warning(f"[clean_up] Failed to delete {path!r} (attempt {attempt}): {e}")
                if attempt < retries:
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[clean_up] Could not remove {path!r} after {retries} attempts.")
