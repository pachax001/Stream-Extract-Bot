# Streams Extractor Bot


#### This Bot can extract audios and subtitles from video files.
#### Send any valid video file and the bot shows you available streams in it that can be extracted!!

## Installation

### Deploy in your vps
#### We are gonna use docker compose to run the bot.
Install docker on your VPS. See official [Docker Docs.](https://docs.docker.com/engine/install/ubuntu/)
<br> After installing docker follow the below steps.</br>
1. Clone the repo and change directory to streamextract
```
git clone https://github.com/pachax001/Stream-Extract-Bot.git streamextract/ && cd streamextract
```
2.Rename sample_config.env to config.env and fill config.env
```
cp sample_config.env config.env
```
Edit config.env
```
nano config.env
```
3. After filling and saving config.env type this command in terminal and press enter.
 ```
sudo docker compose up
```
### Extra

Added /log command to retireve log file of the bot.

Added /restart command to  restart and update bot from repo.
1. To stop docker container
 ```
sudo docker compose down
```
2. To delete stopped containers.
```
sudo docker system prune -a
```
## Configs

* BOT_TOKEN     - Get bot token from @BotFather

* APP_ID        - From my.telegram.org (or @UseTGXBot)

* API_HASH      - From my.telegram.org (or @UseTGXBot)

* OWNER_ID      - Telegram ID of the owner

* AUTH_USERS    - Get from @MissRose_bot by /id command. Put id seperated by commas.

* LOG_CHANNEL   - Create a new channel and add the id of the channel. This channel will send the extracted subtitles or videos.

* LOG_MEDIA_CHANNEL   - Create a new channel and add the id of the channel. This channel for the source file. If this channel is not set LOG_CHANNEL will be used.

* BOT_USERNAME  - Username of the bot. Eg: @Extractorbot

* UPSTREAM_REPO - Repo to update bot on restart.Default is this repo.

* UPSTREAM_BRANCH - Repo branch for update. Default is master.



