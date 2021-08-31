# Discord-Music-Bot
Advanced Discord Music Bot.

### Requirements

For development, you will only need Node.js and a node global package, installed in your environement.

Token Discord [Offical Discord Developer website](https://discord.com/developers)
**How does it work.**

The discord bot uses discord.py[voice] which interfaces through ffmpeg audio(a command line based audio processing software). To retrieve the ffmpeg audio, 
the discord bot extracts videos links using youtube_dl and youtube_search for more accurate searches. Since youtube_dl supports and extracts from various different video sharing platforms,
the bot's streams are not only limited to youtube. 

