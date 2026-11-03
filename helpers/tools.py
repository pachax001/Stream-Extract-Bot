"""Non-blocking process execution and filesystem cleanup helpers."""
import asyncio
import shlex
import shutil
from pathlib import Path
from typing import Optional, Sequence, Union

from helpers.logger import logger


def _prepare_args(command: Union[str, Sequence[str]]) -> list[str]:
    return shlex.split(command) if isinstance(command, str) else [str(x) for x in command]


async def execute(
    command: Union[str, Sequence[str]], timeout: Optional[float] = None
) -> tuple[str, str, int, int]:
    """Run a process without a shell and always reap it on timeout/cancellation."""
    args = _prepare_args(command)
    if not args:
        raise ValueError("Cannot execute an empty command")
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError:
        logger.exception("Unable to start command %s", args[0])
        return "", f"Unable to start {args[0]}", -1, 0

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        logger.error("Command %s exceeded timeout %ss", args[0], timeout)
        return "", f"Command timed out after {timeout}s", -1, proc.pid
    except asyncio.CancelledError:
        if proc.returncode is None:
            proc.kill()
        await proc.communicate()
        raise
    return (
        stdout.decode(errors="replace").strip(),
        stderr.decode(errors="replace").strip(),
        proc.returncode,
        proc.pid,
    )


async def clean_up(
    *paths: Union[str, Path], retries: int = 3, delay: float = 1.0
) -> None:
    """Delete only the supplied files or directories with bounded retries."""
    for raw in paths:
        path = Path(raw)
        for attempt in range(1, retries + 1):
            if not path.exists() and not path.is_symlink():
                break
            try:
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                break
            except OSError:
                logger.exception(
                    "Cleanup failed for %s on attempt %s/%s", path, attempt, retries
                )
                if attempt < retries:
                    await asyncio.sleep(delay)
