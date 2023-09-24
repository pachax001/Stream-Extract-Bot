# Streams Extractor Bot


#### This Bot can extract audios and subtitles from video files.
#### Send any valid video file and the bot shows you available streams in it that can be extracted!!

## Installation

### Deploy in your vps
#### We are gonna use docker compose to run the bot.
Install docker on your VPS. See official [Docker Docs.](https://docs.docker.com/engine/install/ubuntu/)
<br> After installing docker follow the below steps.</br>
1. Clone the repo.
```sh
git clone https://github.com/TroJanzHEX/Streams-Extractor
cd Streams-Extractor
pip3 install -r requirements.txt
# <Create config.py appropriately>
python3 main.py
```

## Configs

* BOT_TOKEN  - Get bot token from @BotFather

* APP_ID        - From my.telegram.org (or @UseTGXBot)

* API_HASH      - From my.telegram.org (or @UseTGXBot)

* AUTH_USERS    - Get from @MissRose_bot by /id command

## Credits

[![TroJanz](https://img.shields.io/badge/Pyrogram%20-%23F37626.svg?&style=for-the-badge&logo=telegram&logoColor=white)](https://github.com/pyrogram/pyrogram)


