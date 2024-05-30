import discord
from discord.ext import commands
import yt_dlp
from fuzzywuzzy import process
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import os

# Bot setup
intents = discord.Intents.default()
intents.presences = True  # Enable presence intent
intents.members = True    # Enable members intent
intents.message_content = True  # Enable message content intent
bot = commands.Bot(command_prefix='$', intents=intents)

# Spotify setup
SPOTIFY_CLIENT_ID = '817d128d2cbc48bebbea3f3e52ea2345'
SPOTIFY_CLIENT_SECRET = 'y7c966497ab5e49778c8cd53cc6bcef71'
sp = Spotify(client_credentials_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

# Global queue and current song
song_queue = []
current_song = None 

# Helper functions
def search_youtube(query):
    ydl_opts = {'format': 'bestaudio'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return info['webpage_url'], info['title']
        except Exception as e:
            print(f"Error searching YouTube: {e}")
            return None, None

def search_spotify(query):
    try:
        results = sp.search(q=query, limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            return track['external_urls']['spotify'], track['name']
    except Exception as e:
        print(f"Error searching Spotify: {e}")
    return None, None

async def play_next(ctx):
    global current_song
    if song_queue:
        current_song = song_queue.pop(0)
        url, title = current_song
        print('FFmpeg options:', discord.FFmpegPCMAudio(executable="ffmpeg", source=url))  # Print FFmpeg options
        await ctx.send(f'Now playing: {title}')
        vc = ctx.voice_client
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=url), after=lambda e: bot.loop.create_task(play_next(ctx)))
    else:
        current_song = None


# Bot commands
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

    url, title = None, None
    if "youtube.com" in query or "youtu.be" in query:
        url, title = query, query
    elif "spotify.com" in query:
        url, title = query, query
    else:
        url, title = search_youtube(query)

    song_queue.append((url, title))
    if not vc.is_playing():
        await play_next(ctx)



    # Rest of your play command logic goes here

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
