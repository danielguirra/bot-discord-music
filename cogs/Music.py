import discord
from discord.ext import commands
import youtube_dl
from youtube_dl import DownloadError
from youtube_search import YoutubeSearch
from urllib3 import exceptions  # HTTPError
import os
import json
import time
import random

import asyncio
from replit import db


class SessionFinished(Exception):
    pass


class Source(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, timeq=None, loop=False, ls=False, volume=0.25):
        super().__init__(source, volume)
        self.data = data
        self.id = data.get('id')
        self.title = data.get('title')
        self.duration = data.get('duration')
        self.author = data.get('author')
        self.ls = data.get('ls')
        self.timeq = timeq
        self.loop = loop
        self.repeat = False

    async def breakdownurl(self, url, serverId, Loop=None, npl=True,):
        ytdl_format_options = {
            'format': 'bestaudio/best',
            'outtmpl': './servers/'+serverId+'/%(id)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': npl,
            'verbose': True,
            'quiet': False,
            'default_search': 'auto',
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_warnings': False,
            # bind to ipv4 since ipv6 addresses cause issues sometimes
            'source_address': '0.0.0.0'
        }
        ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

        try:
            loop = Loop or asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            return data
        except Exception:
            return None

    def set_loop(self, var):
        self.loop = var

    def set_repeat(self, var):
        self.repeat = var

    def set_pausetime(self, tme, pause=False):
        if pause:
            self.timeq[2] = tme
        if not pause:
            self.timeq[1] += int(tme-self.timeq[2])
            self.timeq[2] = 0

    @classmethod
    def streamvideo(cls, data, ss=0, loop=False, options=""):
        if ss:
            print(options)
            ffmpeg_options = {
                'options': '-vn '+options,
                "before_options": "-ss "+str(ss[0])+" -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            }
        else:
            ffmpeg_options = {
                'options': '-vn',  # " -loglevel repeat+verbose"
                "before_options": " -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 1",
            }
        return cls(discord.FFmpegPCMAudio(data['video'], **ffmpeg_options), data=data, timeq=[time.time() if not ss else time.time()+ss[1], 0, 0] if not loop else ["looped", 0, 0], loop=loop)


class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.player = dict()
        self.options = dict()

    @commands.Cog.listener()
    async def on_disconnect(self):
        """
        serverId = str(ctx.guild.id)
        if serverId in db.keys():
           del db[serverId]
        if serverId in self.player:
          self.player[serverId] = None
        if serverId in self.options:
          self.options[serverId] = None
        """

    @commands.command(aliases=['c', 'j', 'connect', 'summon'], pass_context=True)
    async def join(self, ctx):
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        channel = await self.checkconditions(ctx, voice)
        if channel == None:
            return

    @commands.command(aliases=['leav', 'dc', 'leave', 'stop'], pass_context=True)
    async def disconnect(self, ctx):
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        serverId = str(ctx.guild.id)
        if serverId in db.keys():
            del db[serverId]
        if voice and voice.is_connected() and ctx.author.voice and ctx.author.voice.channel == voice.channel:
            if serverId in self.player:
                if self.player[serverId].loop == True:
                    self.player[serverId].set_loop(False)
                voice.stop()
                voice.cleanup()
                await voice.disconnect()
            else:
                voice.cleanup()
                await voice.disconnect()
        else:
            await ctx.send("**O usuário não está conectado ao canal de voz do Bot ou o bot não está conectado**")

    @commands.command(aliases=['q'], pass_context=True)
    async def queue(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        serverId = str(ctx.guild.id)
        id = serverId
        count = 1
        embeds = []
        embed = discord.Embed(title=str(ctx.guild.name) +
                              "'s Queue", colour=0x8e0beb)
        if id in self.player:
            if self.player[id].loop == True:
                embed.set_footer(text="`Loop:`✔️")
            else:
                embed.set_footer(text="`Loop:`❌")
            embed.add_field(name="**Tocando Agora**", value="["+str(self.wslice(self.player[id].title, 50))+"]("+'https://www.youtube.com/watch?v=' +
                            self.player[id].id+")`|"+self.toHMS(self.player[id].duration)+"| Requested by: "+str(self.player[id].author)+"`", inline=False)

            if serverId in db.keys():
                songs = []
                songs = db[serverId]
                for value, song in enumerate(songs):
                    if value == 0:
                        embed.add_field(name='Esperando na Fila', value=str(value+1)+")["+self.wslice(song.get('title'), 50)+"]("+'https://www.youtube.com/watch?v='+song.get(
                            'id')+")`|"+self.toHMS(song.get('duration'))+"| Requested by: "+str(song.get('author'))+"`", inline=False)
                    else:
                        embed.add_field(name='\u200b', value=str(value+1)+")["+self.wslice(song.get('title'), 50)+"]("+'https://www.youtube.com/watch?v='+song.get(
                            'id')+")`|"+self.toHMS(song.get('duration'))+"| Requested by: "+str(song.get('author'))+"`", inline=False)
                    if (value+2) % 10 == 0:
                        embeds.append(embed)
                        count += 1
                        embed = discord.Embed(
                            title=str(ctx.guild.name)+"'s Queue'("+str(count)+")", colour=0x8e0beb)
            embeds.append(embed)
            if len(embeds) > 1:
                await self.pages(ctx.message, embeds)
            else:
                await ctx.send(embed=embeds[0])

        else:
            await ctx.send("**Nenhuma música na fila*")

    async def pages(self, msg, contents):
        pages = len(contents)
        cur_page = 1
        message = await msg.channel.send(embed=contents[cur_page-1])
        # getting the message object for editing and reacting

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        buttons = ["◀️", "▶️"]

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user == msg.author and reaction.emoji in buttons, timeout=60)

                if str(reaction.emoji) == "▶️" and cur_page != pages:
                    cur_page += 1
                    await message.edit(embed=contents[cur_page-1])
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and cur_page > 1:
                    cur_page -= 1
                    await message.edit(embed=contents[cur_page-1])
                    await message.remove_reaction(reaction, user)

                else:
                    await message.remove_reaction(reaction, user)

            except asyncio.TimeoutError:
                await message.delete()
                break

    @commands.command(aliases=['np', 'nowplay'])
    async def nowplaying(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None

        id = str(ctx.guild.id)
        if id in self.player:
            if self.player[id].timeq[0] != "looped":
                if self.player[id].timeq[2] == 0:
                    timepassed = int(
                        time.time()-(self.player[id].timeq[0]+self.player[id].timeq[1]))
                else:
                    timepassed = int(
                        self.player[id].timeq[2]-self.player[id].timeq[0])
                if timepassed > self.player[id].duration:
                    timepassed = self.player[id].duration
                progressbar = self.progressbar(
                    timepassed, self.player[id].duration)
                queuetime = self.toHMS(timepassed)+"/" + \
                    self.toHMS(self.player[id].duration)
            else:
                queuetime = "infite?-looped"
            embed = discord.Embed(
                title="Está Tocando: ", description=progressbar, colour=discord.Colour.blue())
            embed.set_image(
                url="http://img.youtube.com/vi/%s/0.jpg" % self.player[id].id)
            embed.add_field(name='`'+queuetime+'`', value="**[" + self.player[id].title +
                            "]("+'https://www.youtube.com/watch?v='+self.player[id].id+")**", inline=False)
            embed.add_field(
                name="`Requested by: "+self.player[id].author+"`", value='\u200b', inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Não há músicas tocando")

    def wslice(self, word, value):
        if len(word) > value:
            return word[:value-3]+"..."
        else:
            return word

    def progressbar(self, timepassed, duration):
        temp = ["▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬",
                "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬", "▬"]
        temp.insert(int(timepassed/duration*100/4), "🔴")
        return "**|"+"".join(temp)+"|**"

    @commands.command(aliases=['sh'], pass_context=True)
    async def shuffle(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        serverId = str(ctx.guild.id)
        if serverId in db.keys():
            songs = db[serverId]
            random.shuffle(songs)
            db[serverId] = songs
            await ctx.send("`A fila de músicas foi embaralhada 🔀`")

    @commands.command(aliases=['rp'], pass_context=True)
    async def replay(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        serverId = str(ctx.guild.id)
        if serverId in self.player:
            if serverId in db[serverId]:
                songs = db[serverId]
            else:
                songs = []
            songs.insert(0, self.player[serverId].data)
            db[serverId] = songs
            await ctx.send("A música foi enfileirada novamente🔂")

    @commands.command(aliases=['vol'])
    async def volume(self, ctx, volume: int):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        if volume > 250:
            await ctx.send("Sorry, volume has been capped to 250%.")
            volume = 250
        serverId = str(ctx.guild.id)
        if serverId in self.player:
            voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
            voice.source.volume = volume / 500
            await ctx.send(f"O volume foi ajustado {volume}%")
        else:
            await ctx.send(" não estou conectada ao canal.")

    @commands.command(aliases=['pt'], pass_context=True)
    async def playtop(self, ctx):

        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        channel = await self.checkconditions(ctx, voice)
        if channel == None:
            return
        livestream = False
        request = ctx.message.content.split(" ", 1)[1] if len(
            ctx.message.content.split(" ", 1)) > 1 else None
        if request == None:
            return

        if not "." in request:
            await ctx.send("`Pesquisando no Youtubr por "+request)
            try:
                ytrequest = json.loads(YoutubeSearch(
                    request, max_results=1).to_json())
                request = 'https://www.youtube.com/watch?v=' + \
                    str(ytrequest['videos'][0]['id'])
                if ytrequest['videos'][0]['publish_time'] == 0:
                    livestream = True
            except Exception:
                await ctx.send("`Não achei.`")
                return

        serverId = str(ctx.guild.id)
        if serverId in db.keys():
            songs = db[serverId]
        else:
            songs = []

        await ctx.send("`Tentando solicitar "+request+"`")
        info = await Source.breakdownurl(self, request, serverId, Loop=self.bot.loop, npl=False)
        if info == None:
            await ctx.send("`Inválida a URL`")
            return None
        else:
            if 'entries' in info:
                info = info['entries'][0]

        if info['is_live'] == True or info['duration'] == 0.0:
            await ctx.send("Bot currently doesn't support livestreams. Entry denied")
            return None

        playlist = True if 'list=' in info else False
        song_info = {'video': info.get('url', None), 'id': info.get('id', None), 'title': info.get(
            'title', None), 'duration': info.get('duration', None), 'author': str(ctx.author), 'ls': livestream}

        if serverId in self.player:
            songs.insert(0, song_info)
            await self.addedtoqueue(ctx, song_info, playlist, 1)
            db[serverId] = songs
        else:
            songs.append(song_info)
            db[serverId] = songs
            await self.addedtoqueue(ctx, song_info, playlist, 0)
            self.playmusic(ctx, serverId)

        if not playlist:
            return None

        info2 = await Source.breakdownurl(self, request, serverId, Loop=self.bot.loop, npl=False)
        if serverId in db.keys():
            songs = db[serverId]
            if songs[0]['id'] == info.get('id', None):
                firstsong = songs.pop(0)
        else:
            songs = []
            firstsong = None

        if "entries" in info2:
            del info2["entries"][0]
            for entry in reversed(info2["entries"]):
                songs.insert(0, {'video': entry.get('url', None), 'id': entry.get('id', None), 'title': entry.get(
                    'title', None), 'duration': entry.get('duration', None), 'author': str(ctx.author), 'ls': False})
            if firstsong:
                songs.insert(0, firstsong)
            db[serverId] = songs
        else:
            return None

    @commands.command(aliases=['ps'], pass_context=True)
    async def playskip(self, ctx):

        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        channel = await self.checkconditions(ctx, voice)
        if channel == None:
            return

        request = ctx.message.content.split(" ", 1)[1] if len(
            ctx.message.content.split(" ", 1)) > 1 else None
        if request == None:
            return
        livestream = False

        if not "." in request:
            await ctx.send("`Searching for "+request+" on Youtube`")
            try:
                ytrequest = json.loads(YoutubeSearch(
                    request, max_results=1).to_json())
                request = 'https://www.youtube.com/watch?v=' + \
                    str(ytrequest['videos'][0]['id'])
                if ytrequest['videos'][0]['publish_time'] == 0:
                    await ctx.send("Bot doesn't currently have livestream support")
                    return

            except Exception:
                await ctx.send("`No Searches found.`")
                return

        serverId = str(ctx.guild.id)
        if serverId in db.keys():
            songs = db[serverId]
        else:
            songs = []

        await ctx.send("`Searching for "+request+" on Youtube`")
        info = await Source.breakdownurl(self, request, serverId, Loop=self.bot.loop)
        if info == None:
            await ctx.send("`Invalid URL`")
            return None
        else:
            if 'entries' in info:
                info = info['entries'][0]

        if info['is_live'] == True or info['duration'] == 0.0:
            await ctx.send("Bot currently doesn't support livestreams. Entry denied")
            return None
        playlist = True if "list=" in request else False
        song_info = {'video': info.get('url', None), 'id': info.get('id', None), 'title': info.get(
            'title', None), 'duration': info.get('duration', None), 'author': str(ctx.author), 'ls': livestream}

        songs.insert(0, song_info)
        await self.addedtoqueue(ctx, song_info, playlist, 0)
        db[serverId] = songs

        if serverId in self.player:
            if self.player[serverId].loop == True:
                self.player[serverId].set_loop(False)
            if voice.is_playing() or voice.is_paused():
                voice.stop()
            await ctx.send("```Song has been skipped⏭️```")
        else:
            self.playmusic(ctx, serverId)

        if not playlist:
            return None

        info2 = await Source.breakdownurl(self, request, serverId, Loop=self.bot.loop, npl=False)
        if serverId in db.keys():
            songs = db[serverId]
        else:
            songs = []
        if "entries" in info2:
            del info2["entries"][0]
            for entry in reversed(info2["entries"]):
                songs.insert(0, {'video': entry.get('url', None), 'id': entry.get('id', None), 'title': entry.get(
                    'title', None), 'duration': entry.get('duration', None), 'author': str(ctx.author), 'ls': False})
            db[serverId] = songs
        else:
            return None

    @commands.command(aliases=['p', 'pla'], pass_context=True)
    async def play(self, ctx):
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        channel = await self.checkconditions(ctx, voice)
        if channel == None:
            return

        request = ctx.message.content.split(" ", 1)[1] if len(
            ctx.message.content.split(" ", 1)) > 1 else None
        if request == None:
            return
        livestream = False

        if not "." in request:
            await ctx.send("`Searching for "+request+" on Youtube`")
            try:
                ytrequest = json.loads(YoutubeSearch(
                    request, max_results=1).to_json())
                request = 'https://www.youtube.com/watch?v=' + \
                    str(ytrequest['videos'][0]['id'])
                if ytrequest['videos'][0]['publish_time'] == 0:
                    await ctx.send("Bot doesn't currently have livestream support")
                    return

            except Exception:
                await ctx.send("`No searches found.`")
                return None

        serverId = str(ctx.guild.id)
        if serverId in db.keys():
            songs = []
            songs = db[serverId]
        else:
            songs = []

        await ctx.send("`Attempting to request "+request+"`")
        info = await Source.breakdownurl(self, request, serverId, Loop=self.bot.loop)
        if info == None:
            await ctx.send("`Invalid URL`")
            return None
        else:
            if "entries" in info:
                info = info['entries'][0]

        if info['is_live'] == True or info['duration'] == 0.0:
            await ctx.send("Bot currently doesn't support livestreams. Entry denied")
            return None
        playlist = True if 'list=' in request else False
        song_info = {'video': info.get('url', None), 'id': info.get('id', None), 'title': info.get(
            'title', None), 'duration': info.get('duration', None), 'author': str(ctx.author), 'ls': livestream}

        if serverId in self.player:
            songs.append(song_info)
            await self.addedtoqueue(ctx, song_info, playlist, len(songs))
            db[serverId] = songs
        else:
            songs.append(song_info)
            db[serverId] = songs

            await self.addedtoqueue(ctx, song_info, playlist, 0)
            self.playmusic(ctx, serverId)

        if not playlist:
            return None
        info2 = await Source.breakdownurl(self, request, serverId, Loop=self.bot.loop, npl=False)
        if serverId in db.keys():
            songs = db[serverId]
        else:
            songs = []

        if "entries" in info2:
            del info2["entries"][0]
            for entry in info2["entries"]:
                songs.append({'video': entry.get('url', None), 'id': entry.get('id', None), 'title': entry.get(
                    'title', None), 'duration': entry.get('duration', None), 'author': str(ctx.author), 'ls': False})
            db[serverId] = songs
        else:
            return None

    @commands.command(aliases=['paus'], pass_context=True)
    async def pause(self, ctx):
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None

        if voice and voice.is_playing():
            serverId = str(ctx.guild.id)
            self.player[serverId].set_pausetime(time.time(), pause=True)
            voice.pause()
            await ctx.send("Music has been paused")
        else:
            await ctx.send("No music is playing")

    @commands.command(aliases=['resum'], pass_context=True)
    async def resume(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice and voice.is_paused():
            serverId = str(ctx.guild.id)
            self.player[serverId].set_pausetime(time.time())
            voice.resume()
            await ctx.send("Music has been resumed!")

    @commands.command(aliases=['fs', 'skip'], pass_context=True)
    async def forceskip(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_connected():
            serverId = str(ctx.guild.id)
            if serverId in self.player:
                if self.player[serverId].loop == True:
                    self.player[serverId].set_loop(False)
                if voice.is_playing() or voice.is_paused():
                    voice.stop()
                await ctx.send("```Song has been skipped⏭️```")

    @commands.command(aliases=['clea', 'clean'])
    async def clear(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None
        serverId = str(ctx.guild.id)
        author = ctx.message.content.split(" ", 1)[1] if len(
            ctx.message.content.split(" ", 1)) > 1 else None
        if author == None:
            if serverId in db.keys() and len(db[serverId]) > 0:
                del db[serverId]
                await ctx.send("```Queue has been Cleared 🧹```")
            else:
                await ctx.send("```Nothing to Clear ¯\_(ツ)_/¯```")
            return None
        if serverId in db.keys():
            guild = self.bot.get_guild(int(serverId))
            author = int(author[3:-1])
            name = await guild.fetch_member(author)
            if name == None:
                return
            songs = db[serverId]
            maxv = len(songs)
            count = 0
            i = 0
            while i < maxv:
                if songs[i]['author'] == str(name):
                    del songs[i]
                    maxv -= 1
                    count += 1
                else:
                    i += 1
            db[serverId] = songs
            await ctx.send("```css\n"+str(count)+" entries by:"+str(name.name)+" have been cleared from Queue 🧹```")

    @commands.command(aliases=['searc', 's'], pass_context=True)
    async def search(self, ctx):
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None

        channel = await self.checkconditions(ctx, voice)
        if channel == None:
            return
        request = ctx.message.content.split(" ", 1)[1] if len(
            ctx.message.content.split(" ", 1)) > 1 else None
        if not request:
            return None

        await ctx.send("`Searching for "+request+" on Youtube`")
        try:
            embed = discord.Embed(title="Videos:"+request, colour=0x0beb61)
            ytrequest = json.loads(YoutubeSearch(
                request, max_results=7).to_json())
            for i, video in enumerate(ytrequest['videos']):
                embed.add_field(name='\u200b', value='**'+str(i+1)+")["+video.get('title')+']('+'https://www.youtube.com/watch?v='+video.get(
                    'id')+')|('+str(video.get('duration'))+')**\n'+'`Author:'+video.get('channel')+'||Views:'+str(video.get('views'))+'`', inline=False)
            await ctx.send(embed=embed)
        except Exception:
            await ctx.send("`No searches found.`")
            return

        try:
            def check(m):
                return m.content.isdigit() and m.channel == ctx.channel
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            value = int(msg.content)
            livestream = False
            if value <= len(ytrequest['videos']):
                request = 'https://www.youtube.com/watch?v=' + \
                    str(ytrequest['videos'][value-1]['id'])
                info = await Source.breakdownurl(self, request, str(ctx.guild.id), Loop=self.bot.loop)
                if info == None:
                    await ctx.send("`Invalid URL`")
                    return None
                if ytrequest['videos'][value-1]['publish_time'] == 0:
                    livestream = True
                serverId = str(ctx.guild.id)
                if serverId in db.keys():
                    songs = db[serverId]
                else:
                    songs = []
                if serverId in self.player:
                    songs.append({'video': info.get('url', None), 'id': info.get('id', None), 'title': info.get(
                        'title', None), 'duration': info.get('duration', None), 'author': str(ctx.author), 'ls': livestream})
                    db[serverId] = songs
                else:
                    songs.append({'video': info.get('url', None), 'id': info.get('id', None), 'title': info.get(
                        'title', None), 'duration': info.get('duration', None), 'author': str(ctx.author), 'ls': livestream})
                    db[serverId] = songs
                    self.playmusic(ctx, serverId)

        except asyncio.TimeoutError:
            return None

    @commands.command(pass_context=True)
    async def loop(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Use Arctic-Chan in a server please.')
            return None

        serverId = str(ctx.guild.id)
        if serverId in self.player:
            if self.player[serverId].loop == False:
                self.player[serverId].set_loop(True)
                await ctx.send("```Song has been looped🔁```")
            else:
                self.player[serverId].set_loop(False)

    async def checkconditions(self, ctx, voice):
        channel = None
        try:
            if ctx.author.voice.channel:
                channel = ctx.author.voice.channel
        except Exception:
            await ctx.send("**User is not in voice Channel**")
            return None

        if voice and voice.is_connected():
            if voice.channel.id != channel.id and not voice.channel.members:
                await voice.move_to(channel)
            else:
                if voice.channel.id != channel.id:
                    await ctx.send("**Bot already connected to different channel**")
        else:
            try:
                serverId = str(ctx.guild.id)
                await channel.connect(timeout=60.0, reconnect=True)
                self.options[serverId] = ["", dict(), 0]
                self.options[serverId][1]['volume'] = 75
                self.options[serverId][1]['temp'] = ""
            except asyncio.TimeoutError:
                print("Bot has left")
        return channel

    def playmusic(self, ctx, id, nowplaying=None, loop=False, options=None):
        if not options:
            options = self.options[id][0] if self.options[id][1]['temp'] == None else self.options[id][1]['temp']
        print(options)
        if nowplaying:
            player = Source.streamvideo(
                nowplaying[0], loop=loop, ss=nowplaying[1], options=options)
            self.player[id] = player
            ctx.voice_client.play(player, after=lambda e: self.playmusic(
                ctx, id) and self.reseteffects(id) if not player.repeat else player.set_repeat(False))
            return None
        if id in self.player:
            if self.player[id].loop == True:
                loop = True
                nowplaying = self.player[id].data
        if not nowplaying:
            if id in db.keys() and len(db[id]) > 0:
                songs = db[id]
                nowplaying = songs.pop(0)
                db[id] = songs
            else:
                self.player.pop(id, None)
                return None
        player = Source.streamvideo(nowplaying, loop=loop, options=options)
        self.player[id] = player
        ctx.voice_client.play(player, after=lambda e: self.playmusic(
            ctx, id) and self.reseteffects(id) if not player.repeat else player.set_repeat(False))

    def reseteffects(self, id):
        if self.options[id][1]['temp'] != None:
            self.options[id][1]['temp'] = ""

    async def addedtoqueue(self, ctx, data, playlist, position: int):
        serverId = str(ctx.guild.id)
        if position == 0:
            position = "Currently Playing"
        else:
            position = str(position)
        if isinstance(data['duration'], int) and data['duration'] != 0:
            duration = self.toHMS(data['duration'])
        else:
            duration = "livestream"
        if position != "Currently Playing":
            dtp = self.toHMS(self.durationtillplay(serverId, int(position)))
        else:
            dtp = "Now"
        if not playlist:
            notif = discord.Embed(title="Song Added to queue", description="**["+data.get(
                'title')+"](https://www.youtube.com/watch?v="+data.get('id')+")**", colour=random.randint(0, 0xffffff))
            notif.add_field(name="Till Played", value=dtp if not data.get(
                'ls') and dtp else "livestream", inline=True)
            notif.add_field(name="Song Duration", value=duration if not data.get(
                'ls') else "livestream", inline=True)
            notif.add_field(name="Position", value=position, inline=False)
            notif.set_thumbnail(
                url="http://img.youtube.com/vi/%s/0.jpg" % data.get('id'))

        else:
            notif = discord.Embed(title="Playlist added/being added to queue", description="**["+data.get(
                'title')+"](https://www.youtube.com/watch?v="+data.get('id')+")**", colour=random.randint(0, 0xffffff))
            notif.add_field(name="**Till Played**",
                            value="`"+dtp+"`", inline=True)
            notif.add_field(name="**Song Duration**",
                            value="`"+duration+"`", inline=True)
            notif.add_field(name="**Position**", value=position, inline=False)
            notif.set_thumbnail(
                url="http://img.youtube.com/vi/%s/0.jpg" % data.get('id'))
            notif.set_footer(text="`Playlist info may take some time.`")
        await ctx.send(embed=notif)

    def durationtillplay(self, id, position):
        td = 0
        if id in db.keys():
            songs = db[id]
            for i in range(position-1):
                td += songs[i].get('duration')
        if self.player[id].timeq[2] == 0:
            td += self.player[id].duration - \
                (int(time.time() -
                 (self.player[id].timeq[0]+self.player[id].timeq[1])))
        else:
            td += self.player[id].duration - \
                (int(self.player[id].timeq[2]-self.player[id].timeq[0]))
        return td

    def toHMS(self, s):
        if isinstance(s, int):
            if s > 36000:
                return "%02d:%02d:%02d" % (s/60**2, s/60 % 60, s % 60)
            elif s > 3600:
                return "%d:%02d:%02d" % (s/60**2, s/60 % 60, s % 60)
            elif s > 600:
                return "%02d:%02d" % (s/60 % 60, s % 60)
            else:
                return "%d:%02d" % (s/60 % 60, s % 60)
        else:
            return ""

    @commands.command(aliases=['dl'], pass_context=True)
    async def download(self, ctx, *, url):
        id = str(ctx.author.id)
        member = ctx.author
        dlopts = {
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': "./download/"+id+"/%(id)s.%(ext)s",
            'default_search': 'auto',
            'max_filesize': 60000000,
            'quiet': True,
            'noplaylist': True,
        }
        with youtube_dl.YoutubeDL(dlopts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info['duration'] > 600 or info['duration'] == 0:
                await ctx.send('Song duration can not be more than 10 mins')
            else:
                try:
                    ydl.download([url])
                except DownloadError:
                    await ctx.send('Download failed.Make sure file is smaller than 60mb.')
        for file in os.listdir('./download/'+id):
            if file.endswith('.mp3'):
                user = await member.create_dm()
                await user.send(file=discord.File(r'./download'+id+'/%(title).mp3'))
            else:
                os.remove('./download/'+id+'/'+file)
        os.rmdir('./download/'+id)


def setup(bot):
    bot.add_cog(Music(bot))
