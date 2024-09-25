import os
import shlex
import asyncio
from helpers.logger import logger
from typing import Tuple
import time

async def execute(cmnd: str) -> Tuple[str, str, int, int]:
    try:
        cmnds = shlex.split(cmnd)
        process = await asyncio.create_subprocess_exec(
            *cmnds,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return (stdout.decode('utf-8', 'replace').strip(),
                stderr.decode('utf-8', 'replace').strip(),
                process.returncode,
                process.pid)
    except Exception as e:
        logger.error(f"Error while executing command: {e}")
        return ("", "", 1, 0)

async def clean_up(input1, input2=None, filename=None):
    retries = 3
    while retries > 0:
        logger.info(f"trying to delete file {filename} in input1: attempt {3 - retries + 1}")
        try:
            if input1 and os.path.exists(input1):
                os.remove(input1)
                logger.info(f"Deleted file {filename} in input1")
                break
            #os.remove(input1)
        except Exception as e:
            logger.error(f"Error while deleting file {filename} in input1: {e}")
            retries -= 1
            if retries == 0:
                logger.error(f"Failed to delete file {filename} in input1")
                break
            time.sleep(1)
        try:
            if input2 and os.path.exists(input2):
                os.remove(input2)
        except Exception as e:
            logger.error(f"Error while deleting file{filename} in input2: {e}")
            pass        