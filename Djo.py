import discord
from discord.ext import commands
import yt_dlp
import os

# Bot setup
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='$', intents=intents)

# Global queue and current song
song_queue = []
current_song = None

# Helper functions
def search_youtube(query):
    ydl_opts = {'format': 'bestaudio'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return info['url'], info['title']
        except Exception as e:
            print(f"Error searching YouTube: {e}")
            return None, None

async def play_next(ctx):
    global current_song
    if song_queue:
        current_song = song_queue.pop(0)
        url, title = current_song
        await ctx.send(f'Now playing: {title}')
        vc = ctx.voice_client
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }
        vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options), after=lambda e: bot.loop.create_task(play_next(ctx)))
    else:
        current_song = None

@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send('You need to join a voice channel first.')
        return

    vc = ctx.voice_client
    if not vc:
        vc = await ctx.author.voice.channel.connect()

        # Check bot's permissions in the voice channel
        permissions = vc.channel.permissions_for(ctx.guild.me)
        if not permissions.connect or not permissions.speak:
            await ctx.send("I don't have permission to connect or speak in that channel.")
            return

        print('Bot permissions:', permissions)  # Print the bot's permissions

    if "youtube.com" in query or "youtu.be" in query:
        try:
            # Check if the link is a playlist
            if "playlist" in query:
                # Extract video titles from the playlist
                ydl_opts = {
                    'extract_flat': True,
                    'format': 'bestaudio'
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    playlist_info = ydl.extract_info(query, download=False)
                    titles = [entry['title'] for entry in playlist_info['entries']]

                # Search for each title on YouTube and add to the queue
                for title in titles:
                    url, title = search_youtube(title)
                    if url and title:
                        song_queue.append((url, title))
            else:
                # Get the video URL and title
                ydl_opts = {'format': 'bestaudio'}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    url = info['url']
                    title = info['title']
                    song_queue.append((url, title))
        except Exception as e:
            print(f"Error processing YouTube link: {e}")
            await ctx.send("An error occurred while processing the YouTube link.")
            return
    else:
        url, title = search_youtube(query)

    if url and title:
        song_queue.append((url, title))
        if not vc.is_playing():
            await play_next(ctx)

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc.is_playing():
        vc.stop()

@bot.command()
async def stop(ctx):
    global song_queue
    song_queue = []
    vc = ctx.voice_client
    if vc.is_playing():
        vc.stop()
    await vc.disconnect()

@bot.command()
async def clear(ctx):
    global song_queue
    song_queue = []
    await ctx.send('Queue cleared.')

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')

token = os.environ.get('DISCORD_TOKEN')
bot.run(token)
