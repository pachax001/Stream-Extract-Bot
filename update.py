from os import path as opath, getenv
from subprocess import run as srun
from dotenv import load_dotenv
from helpers.logger import logger
from os import path as ospath, environ, remove
if ospath.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

load_dotenv('config.env', override=True)

UPSTREAM_REPO = getenv('UPSTREAM_REPO', "https://github.com/pachax001/Stream-Extract-Bot")
UPSTREAM_BRANCH = getenv('UPSTREAM_BRANCH', "main")

if UPSTREAM_REPO is not None:
    if opath.exists('.git'):
        srun(["rm", "-rf", ".git"])
        
    update = srun([f"git init -q \
                     && git config --global user.email pachax001@gmail.com \
                     && git config --global user.name pachax001 \
                     && git add . \
                     && git commit -sm update -q \
                     && git remote add origin {UPSTREAM_REPO} \
                     && git fetch origin -q \
                     && git reset --hard origin/{UPSTREAM_BRANCH} -q"], shell=True)

    if update.returncode == 0:
        logger.info('Successfully updated with latest commit from UPSTREAM_REPO')
        
    else:
        logger.error('Something went wrong while updating, check UPSTREAM_REPO if valid or not!')