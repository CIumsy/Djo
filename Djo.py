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
        await ctx.send(f'Now playing: {title}')
        vc = ctx.voice_client
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=url), after=lambda e: bot.loop.create_task(play_next(ctx)))
    else:
        current_song = None

# Bot commands
@bot.command()
async def play(ctx, *, query):
    # Check if the author is in a voice channel
    if not ctx.author.voice:
        await ctx.send('You need to join a voice channel first.')
        return

    # Check if the bot is already in a voice channel
    vc = ctx.voice_client
    if vc:
        if vc.channel != ctx.author.voice.channel:
            await vc.move_to(ctx.author.voice.channel)
    else:
        # Bot is not in a voice channel, so connect to the author's voice channel
        vc = await ctx.author.voice.channel.connect()

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
