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
2.Fill the variables in [config.py](https://github.com/pachax001/Stream-Extract-Bot/blob/main/config.py)
<br> [Click here](https://github.com/pachax001/Stream-Extract-Bot/blob/main/README.md#configs) for more info on config. </br>

[In this line](https://github.com/pachax001/Stream-Extract-Bot/blob/56bb5983b80f833ee625adb6352bfba4db357cee/main.py#L23) replace the number with your telegram id.

3. After filling and saving config.py type this command in terminal and press enter.
 ```
sudo docker compose up
```
### Extra
1. To stop docker container
 ```
sudo docker compose down
```
2. To delete stopped containers.
```
sudo docker system prune
```
## Configs

* BOT_TOKEN     - Get bot token from @BotFather

* APP_ID        - From my.telegram.org (or @UseTGXBot)

* API_HASH      - From my.telegram.org (or @UseTGXBot)

* AUTH_USERS    - Get from @MissRose_bot by /id command. Put id seperated by spaces.

* LOG_CHANNEL   - Create a new channel and add the id of the channel. Remember to put the log channel ID also to the AUTH_USERS.

* BOT_USERNAME  - Username of the bot. Do not put @ before the username. Only add the name.


