import asyncio
import re

import discord
import youtube_dl
from discord.ext import commands

import bot_token
from youtube_utility import *

ydl_opts = {'format': 'bestaudio'}
TOKEN = bot_token.discord_token
bot_command_prefix = '//'
client = commands.Bot(command_prefix=bot_command_prefix)
ffmpeg_exe = r'./ffmpeg/bin/ffmpeg.exe'
url_pattern = 'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 0'}

clients = {}


class PlayQueueComponent:
    ctx = None
    info = None

    def __init__(self, ctx, info):
        self.ctx = ctx
        self.info = info


class GuildClient:
    guild_id = None
    voice_client = None
    play_queue = []
    loop_mode = 0
    pausing = None

    def __init__(self, guild_id: str, voice_client):
        self.guild_id = guild_id
        self.voice_client = voice_client
        self.pausing = False

    def add(self, ctx, url: str):
        self.play_queue.append(PlayQueueComponent(ctx, url))

    def remove(self, index: int):
        self.play_queue.remove(index)

    def play1(self):
        while len(self.play_queue) > 0:
            if self.voice_client is None:
                break

            """info = YoutubeUtility.get_video_info(self.play_queue[0].url)
            if info is None:
                self.play_queue[0].ctx.send('')
                return"""

            """link = info.get_best_audio()['url']"""
            info = self.play_queue[0].info
            link = info['formats'][-1]['url']
            embed = discord.Embed(title=info['title'], color=0x00ff00)
            embed.set_author(name='再生中')
            if info['request_type'] == 'youtube_dl':
                try:
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(info['webpage_url'], download=False)
                        with open('youtube_utility/response.json', 'w') as f:
                            f.write(json.dumps(info, indent=4))
                except youtube_dl.DownloadError:
                    client.loop.create_task(self.play_queue[0].ctx.send(
                        embed=discord.Embed(title='Error', color=0xff0000, description='An error has occurred')))
                    continue
                embed.description = info['uploader']
                embed.url = info['webpage_url']
                embed.set_image(url=info['thumbnail'])
            client.loop.create_task(self.play_queue[0].ctx.send(embed=embed))
            if self.voice_client is None:
                break
            self.voice_client.play(
                discord.FFmpegPCMAudio(link, executable=r'./ffmpeg/ffmpeg.exe', **ffmpeg_options))
            while self.voice_client.is_playing() or self.pausing:
                asyncio.run(asyncio.sleep(5))
            if len(self.play_queue) != 0 and self.loop_mode != 2:
                if self.loop_mode == 1:
                    self.play_queue.append(self.play_queue[0])
                self.play_queue.pop(0)

    async def play(self, first: bool):
        print('called_play')
        if (not first) and len(self.play_queue) != 0 and self.loop_mode != 2:
            if self.loop_mode == 1:
                self.play_queue.append(self.play_queue[0])
            self.play_queue.pop(0)
        if self.voice_client is None or self.voice_client.is_playing():
            return
        info = self.play_queue[0].info
        link = info['formats'][-1]['url']
        embed = discord.Embed(title=info['title'], color=0x00ff00)
        embed.set_author(name='再生中')
        if info['request_type'] == 'youtube_dl':
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(info['webpage_url'], download=False)
                    with open('youtube_utility/response.json', 'w') as f:
                        f.write(json.dumps(info, indent=4))
            except youtube_dl.DownloadError:
                await self.play_queue[0].ctx.send(
                    embed=discord.Embed(title='Error', color=0xff0000, description='An error has occurred'))
            embed.description = info['uploader']
            embed.url = info['webpage_url']
            embed.set_image(url=info['thumbnail'])
        await self.play_queue[0].ctx.send(embed=embed)

        async def play_next():
            await self.play(False)

        self.voice_client.play(
            discord.FFmpegPCMAudio(link, **ffmpeg_options),
            after=play_next)


@client.event
async def on_ready():
    print('[' + str(datetime.now()) + '] Launch successful')


@client.command()
async def connect(ctx):
    if not ctx.message.guild:
        return False

    if ctx.author.voice is None:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='ボイスチャンネルに接続していません\nボイスチャンネルに接続してから再度実行してください'))
        return False
    elif ctx.guild.voice_client:
        if ctx.author.voice.channel == ctx.guild.voice_client.channel:
            await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                               description='既に接続済みです'))
            return False
        else:
            voice_channel = ctx.author.voice.channel
            await ctx.voice_client.move_to(voice_channel)
            return True
    else:
        await ctx.send(embed=discord.Embed(title='ボイスチャンネル接続', color=0x00ff00,
                                           description='**' + ctx.guild.name + ' : ' + ctx.author.voice.channel.name
                                                       + '**に接続しました'))
        global clients
        await ctx.author.voice.channel.connect()
        clients[str(ctx.guild.id)] = GuildClient(str(ctx.guild.id), ctx.guild.voice_client)
        print(
            '[' + str(datetime.now()) + '] Connected [' + ctx.guild.name + ' : ' + ctx.author.voice.channel.name + ']')
        return True


@client.command()
async def join(ctx):
    return await connect(ctx)


@client.command()
async def disconnect(ctx):
    if not ctx.message.guild:
        return

    if ctx.voice_client is None:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='まだボイスチャンネルに接続していません'))
    else:
        global clients
        clients.pop(str(ctx.guild.id))
        await ctx.voice_client.disconnect()
        await ctx.send(embed=discord.Embed(title='ボイスチャンネル切断', color=0x00ff00,
                                           description='切断しました'))
        print('[' + str(
            datetime.now()) + '] Disconnected [' + ctx.guild.name + ' - ' + ctx.author.voice.channel.name + ']')


@client.command()
async def leave(ctx):
    await disconnect(ctx)


@client.command()
async def p(ctx, *args):
    await play(ctx, *args)


@client.command()
async def play(ctx, *args):
    if ctx.guild.voice_client is None:
        joined = await join(ctx)
        if not joined:
            return

    if len(args) == 0:
        await ctx.send(embed=discord.Embed(title='使用方法', color=0xffff00,
                                           description='//play [ビデオURL]'))
        return

    received_url = str(args[0])

    global clients
    cl = clients[str(ctx.guild.id)]
    if received_url.upper() == '-FILE' and len(ctx.message.attachments) != 0:
        attach = ctx.message.attachments[0]
        info = {
            'title': attach.filename,
            'formats': [
                {
                    'url': attach.url
                }
            ],
            'request_type': 'file'
        }
        cl.add(ctx, info)
    else:
        if (not re.match(url_pattern, received_url)) or len(args) != 1:
            keyword = ''
            for i in range(len(args)):
                if i != 0:
                    keyword += '\u0020'
                keyword += args[i]
            received_url = YoutubeUtility.search_video(keyword)[0].get_video_url()

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(received_url, download=False)
                info['request_type'] = 'youtube_dl'
                is_playlist = '_type' in info.keys() and info['_type'] == 'playlist'
                if is_playlist:
                    embed = discord.Embed(title=info['title'], url=info['webpage_url'], color=0x00ff00)
                    playlist_length = len(info['entries'])
                    embed.description = str(playlist_length) + '曲を追加しました'
                    embed.set_author(name="プレイリストに追加")
                    for i in range(playlist_length):
                        ent = info['entries'][i]
                        ent['request_type'] = 'youtube_dl'
                        cl.add(ctx, ent)
                        if i < 25:
                            embed.add_field(name=str(i + 1), value=ent['title'], inline=False)
                        if i == 26:
                            embed.set_footer(text='更に' + str(playlist_length - 25) + '曲')
                    await ctx.send(embed=embed)
                else:
                    cl.add(ctx, info)
        except youtube_dl.DownloadError:
            await ctx.send(embed=discord.Embed(title='Error', color=0xff0000,
                                               description='An error has occurred'))
            return

    if not ctx.guild.voice_client.is_playing():
        await cl.play(True)
    elif not is_playlist:
        embed = discord.Embed(title=info['title'], color=0x00ff00)
        embed.set_author(name='プレイリストに追加')
        if info['request_type'] == 'youtube_dl':
            embed.url = info['webpage_url']
            embed.description = info['uploader']
            embed.set_image(url=info['thumbnail'])
        await ctx.send(embed=embed)


@client.command()
async def search(ctx, *args):
    if len(args) == 0:
        await ctx.send(embed=discord.Embed(title='使用方法', color=0xffff00,
                                           description='//search [検索ワード]'))
    keyword = ''
    for i in range(len(args)):
        if i != 0:
            keyword += '\u0020'
        keyword += args[i]
    result = YoutubeUtility.search_video(keyword)
    res_message = ''
    for i in range(5):
        if i != 0:
            res_message += '\n'
        res_message += str(i + 1) + '. ' + result[i].title + ' - [by ' + result[i].uploader_name + ']'
    await ctx.send('```' + res_message + '```')


@client.command()
async def get_url(ctx, *args):
    if len(args) == 0:
        await ctx.send(embed=discord.Embed(title='使用方法', color=0xffff00,
                                           description='//get_url [検索ワード]'))
    keyword = ''
    for i in range(len(args)):
        if i != 0:
            keyword += '\u0020'
        keyword += args[i]
    await ctx.send(YoutubeUtility.search_video(keyword)[0].get_video_url())


@client.command()
async def get_info(ctx, *args):
    if len(args) == 0:
        await ctx.send(embed=discord.Embed(title='使用方法', color=0xffff00,
                                           description='//get_url [検索ワードまたURL]'))
        return
    received_url = str(args[0])
    if (not re.match(url_pattern, received_url)) or len(args) != 1:
        keyword = ''
        for i in range(len(args)):
            if i != 0:
                keyword += '\u0020'
            keyword += args[i]
        received_url = YoutubeUtility.search_video(keyword)[0].get_video_url()
    result = YoutubeUtility.get_video_info(received_url)
    if result is None:
        await ctx.send('An error has occurred')
        return
    result = result.get_all()
    result_str = ''
    for i in range(len(result)):
        if i == len(result) - 1:
            result_str += '```'
        result_str += result[i]
    result_str += '```'
    if len(result_str) > 2000:
        result_str = result_str[:1990] + '\n…```'
    await ctx.send(result_str)


@client.command()
async def remove(ctx, *args):
    if len(args) != 1 or not args[0].isdicimal():
        await ctx.send(embed=discord.Embed(title='使用方法', color=0xffff00,
                                           description='//remove [キュー番号]'))
        return

    global clients
    cl = clients[str(ctx.guild.id)]
    if len(cl.play_queue) < int(args[0]) or int(args[0]) != float(args[0]) or int(args[0]) <= 0:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='キュー番号が無効です'))
        return

    cl.remove(int(args[0]))


@client.command()
async def skip(ctx):
    global clients
    cl = clients[str(ctx.guild.id)]
    if cl.voice_client is None:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='現在再生中ではありません'))
        return
    cl.voice_client.pause()


@client.command()
async def pause(ctx):
    global clients

    cl = clients[str(ctx.guild.id)]
    if cl.voice_client is None or cl.pausing:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='現在再生中ではありません'))
        return
    else:
        cl.pausing = True
        cl.voice_client.pause()
        await ctx.send(embed=discord.Embed(title='一時停止', color=0xffff00,
                                           description='現在一時停止中です。\n`//resume`で再生を再開出来ます。'))


@client.command()
async def resume(ctx):
    global clients

    cl = clients[str(ctx.guild.id)]
    if cl.voice_client is None:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='現在再生中ではありません'))
        return
    elif not cl.pausing:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='現在一時停止中ではありません'))
        return
    else:
        cl.pausing = False
        cl.voice_client.resume()
        await ctx.send(embed=discord.Embed(title='再生中', color=0x00ff00,
                                           description='再生を再開しました'))


@client.command()
async def stop(ctx):
    global clients

    cl = clients[str(ctx.guild.id)]
    if cl.voice_client is None:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='現在再生中ではありません'))
        return
    cl.play_queue = []
    cl.voice_client.pause()


@client.command()
async def loop(ctx):
    global clients
    if ctx.guild.voice_client is None:
        await ctx.send(embed=discord.Embed(title='エラー', color=0xffff00,
                                           description='まだボイスチャンネルに接続していません'))
        return
    cl = clients[str(ctx.guild.id)]
    cl.loop_mode = (cl.loop_mode + 1) % 3
    lp = cl.loop_mode
    if lp == 1:
        await ctx.send(embed=discord.Embed(title='ループ', color=0x00ff00,
                                           description='プレイリストをループします'))
    elif lp == 2:
        await ctx.send(embed=discord.Embed(title='ループ', color=0x00ff00,
                                           description='現在の曲をループします'))
    else:
        await ctx.send(embed=discord.Embed(title='ループ', color=0x00ff00,
                                           description='ループが無効になりました'))


@client.event
async def on_message(message):
    if message.content.startswith(bot_command_prefix):
        command = message.content.replace(bot_command_prefix, '')
        if '\u0020' in command:
            command = command[0:message.content.find('\u0020') - 2]
        if command in [com.name for com in client.commands]:
            await client.process_commands(message)
        else:
            await message.channel.send('Unknown command')


client.run(TOKEN)
