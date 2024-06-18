import discord
from discord.ext import commands
import yt_dlp
import os
import random
from pydub import AudioSegment
from flask import Flask

# Bot setup
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='$', intents=intents)

# Global variables
song_queue = []
current_song = None
loop_mode = False

# Flask setup
app = Flask(__name__)

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
    global loop_mode

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
        if loop_mode:
            song_queue.append(current_song)
    else:
        current_song = None
        if loop_mode and current_song:
            song_queue.append(current_song)

@bot.command(aliases=['p'])
async def play(ctx, *, query):
    global current_song

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
                        if vc.is_playing() or vc.is_paused():
                            await ctx.send(f'Added **{title}** to the queue.')
            else:
                # Get the video URL and title
                ydl_opts = {'format': 'bestaudio'}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    url = info['url']
                    title = info['title']
                    song_queue.append((url, title))
                    if vc.is_playing() or vc.is_paused():
                        await ctx.send(f'Added **{title}** to the queue.')
        except Exception as e:
            print(f"Error processing YouTube link: {e}")
            await ctx.send("An error occurred while processing the YouTube link.")
            return
    else:
        url, title = search_youtube(query)
        if url and title:
            song_queue.append((url, title))
            if vc.is_playing() or vc.is_paused():
                await ctx.send(f'Added **{title}** to the queue.')

    if not vc.is_playing() and not vc.is_paused():
        await play_next(ctx)

@bot.command(aliases=['q'])
async def queue(ctx):
    if song_queue:
        queue_list = '\n'.join([f'{i+1}. {title}' for i, (url, title) in enumerate(song_queue)])
        await ctx.send(f'Current queue:\n{queue_list}')
    else:
        await ctx.send('The queue is empty.')

@bot.command(aliases=['s'])
async def skip(ctx):
    global current_song
    vc = ctx.voice_client
    if vc.is_playing() or vc.is_paused():
        if current_song:
            await ctx.send(f'Skipped **{current_song[1]}**')
        vc.stop()

@bot.command()
async def stop(ctx):
    global song_queue
    song_queue = []
    vc = ctx.voice_client
    if vc.is_playing() or vc.is_paused():
        vc.stop()
    await vc.disconnect()

@bot.command(aliases=['c'])
async def clear(ctx):
    global song_queue
    song_queue = []
    await ctx.send('Queue cleared.')

@bot.command(aliases=['r'])
async def remove(ctx, index: int):
    """Remove a song from the queue by its position."""
    if 0 < index <= len(song_queue):
        removed_song = song_queue.pop(index - 1)
        await ctx.send(f'Removed **{removed_song[1]}** from the queue.')
    else:
        await ctx.send('Invalid position. Please provide a valid song number from the queue.')

@bot.command()
async def qup(ctx, index: int):
    """Move a song from its current position in the queue to the first position."""
    if 0 < index <= len(song_queue):
        song = song_queue.pop(index - 1)
        song_queue.insert(0, song)
        await ctx.send(f'Moved **{song[1]}** to the top of the queue.')
    else:
        await ctx.send('Invalid position. Please provide a valid song number from the queue.')

@bot.command()
async def shuffle(ctx):
    """Shuffle the songs in the queue randomly."""
    global song_queue
    if song_queue:
        random.shuffle(song_queue)
        await ctx.send('Queue shuffled.')
    else:
        await ctx.send('The queue is empty, nothing to shuffle.')

@bot.command(aliases=['pause'])
async def pause_music(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send('Paused the music.')
    else:
        await ctx.send('No music is playing right now.')

@bot.command(aliases=['resume'])
async def resume_music(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send('Resumed the music.')
    else:
        await ctx.send('Music is not paused right now.')

@bot.command(aliases=['np'])
async def now_playing(ctx):
    global current_song
    if current_song:
        await ctx.send(f'Now playing: **{current_song[1]}**')
    else:
        await ctx.send('No music is playing right now.')

@bot.command(aliases=['loop'])
async def toggle_loop(ctx):
    global loop_mode
    loop_mode = not loop_mode
    if loop_mode:
        await ctx.send('Loop mode enabled.')
    else:
        await ctx.send('Loop mode disabled.')

@bot.command()
async def seek(ctx, position):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        total_seconds = parse_time(position)
        if total_seconds is not None:
            vc.stop()
            vc.play(discord.FFmpegPCMAudio(current_song[0], options=f'-vn -ss {total_seconds}'), after=lambda e: bot.loop.create_task(play_next(ctx)))
            await ctx.send(f'Seeking to {position}.')
        else:
            await ctx.send('Invalid position format. Please use HH:MM:SS or MM:SS.')
    else:
        await ctx.send('No music is playing right now.')

def parse_time(position):
    parts = position.split(':')
    if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 2 and parts[1].isdigit() and len(parts[1]) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3 and parts[0].isdigit() and len(parts[0]) == 2 and parts[1].isdigit() and len(parts[1]) == 2 and parts[2].isdigit() and len(parts[2]) == 2:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return None

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')

# Flask route for basic web service
@app.route('/')
def index():
    return "Bot is online."

# Run Flask web service in the background
if __name__ == '__main__':
    bot.run('YOUR_DISCORD_BOT_TOKEN')  # Replace with your actual bot token
    app.run(debug=True, port=8080)  # Flask runs on port 8080 (specified by Render.com)

# End of bot script
