import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
import asyncio
from collections import defaultdict,deque



load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("SERVER_ID_K")
SONG_QUEUES = defaultdict(deque)
# SONG_QUEUES={}

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query,ydl_opts))

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=SERVER_ID))
        print(f"Synced {len(synced)} command(s) to guild {SERVER_ID}")
    except Exception as e:
        print(f"Sync failed: {e}")
    print(f"{bot.user} is online!")


@bot.tree.command(name="skip", description="Skips the current playing song",guild=discord.Object(id=SERVER_ID))
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Skipped the current song.")
    else:
        await interaction.response.send_message("Not playing anything to skip.")

@bot.tree.command(name="pause", description="Pause the currently playing song.",guild=discord.Object(id=SERVER_ID))
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if something is actually playing
    if not voice_client.is_playing():
        return await interaction.response.send_message("Nothing is currently playing.")
    
    # Pause the track
    voice_client.pause()
    await interaction.response.send_message("Playback paused!")


@bot.tree.command(name="resume", description="Resume the currently paused song.",guild=discord.Object(id=SERVER_ID))
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if it's actually paused
    if not voice_client.is_paused():
        return await interaction.response.send_message("I'm not paused right now.")
    
    # Resume playback
    voice_client.resume()
    await interaction.response.send_message("Playback resumed!")


@bot.tree.command(name="stop", description="Stop playback and clear the queue.",guild=discord.Object(id=SERVER_ID))
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if not voice_client or not voice_client.is_connected():
        return await interaction.response.send_message("I'm not connected to any voice channel.")

    # Clear the guild's queue
    guild_id_str = str(interaction.guild_id)
    if guild_id_str in SONG_QUEUES:
        SONG_QUEUES[guild_id_str].clear()

    # If something is playing or paused, stop it
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    # (Optional) Disconnect from the channel
    await voice_client.disconnect()

    await interaction.response.send_message("Stopped playback and disconnected!")


@bot.tree.command(name='play', description="Paly a song or add it to the queue", guild=discord.Object(id=SERVER_ID))
@app_commands.describe(song_query="Search query")
async def play(interaction: discord.Interaction, song_query:str):
    await interaction.response.defer()

    if interaction.user.voice is None :
        await interaction.followup.send("You must be in a voice channel.")
        return
    
    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)

    ydl_options = {
        "format": "bestaudio[abr<=96]/bestaudio",
        "noplaylist": True,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
    }
    
    song_long = song_query.split("&")
    song = song_long[0]
    query = "ytsearch1: " + song
    results = await search_ytdlp_async(query, ydl_options)

    if not results or "entries" not in results:
        await interaction.followup.send("No search results found. Please try a different keyword or link.")
        return

    tracks = results["entries"]
  
    if not tracks:
        await interaction.followup.send("No songs were found. Please check the link or search query.")
        return

    first_track = tracks[0]
    audio_url = first_track["url"]
    title = first_track.get("title", "Untitled")
    duration = f"{first_track['duration'] // 60}:{first_track['duration'] % 60:02}" if 'duration' in first_track else "?:??"


    guild_id = str(interaction.guild_id)
    if SONG_QUEUES.get(guild_id) is None:
        SONG_QUEUES[guild_id] = deque()

    SONG_QUEUES[guild_id].append({
        "title": title,
        "url": audio_url,
        "duration": duration,
        "requested_by": interaction.user.display_name
    })

    # SONG_QUEUES[guild_id].append((audio_url, title))
    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(f"Added to queue: **{title}**")
    else:
        await interaction.followup.send(f"Now playing: **{title}**")
        await play_next_song(voice_client, guild_id, interaction.channel)


async def play_next_song(voice_client, guild_id, channel):
    if SONG_QUEUES[guild_id]:
        song = SONG_QUEUES[guild_id].popleft()
        audio_url = song["url"]
        title = song["title"]


        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn -c:a libopus -b:a 128k",
            # Remove executable if FFmpeg is in PATH
        }

        source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg.exe")

        def after_play(error):
            if error:
                print(f"Error playing {title}: {error}")
            asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)

        voice_client.play(source, after=after_play)
        asyncio.create_task(channel.send(f"Now playing: **{title}**"))
    else:
        # await voice_client.disconnect()
        asyncio.create_task(channel.send(f"The list is empty."))
        SONG_QUEUES[guild_id] = deque()


@bot.tree.command(name="queue", description="Check queue songs", guild=discord.Object(id=SERVER_ID))
async def check_queue(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    queue = SONG_QUEUES.get(guild_id, [])

    if not queue:
        await interaction.response.send_message("The queue is currently empty.")
        return

    queue_list = "\n".join(
        f"{idx+1}. {song['title']} ({song['duration']}) - requested by {song['requested_by']}"
        for idx, song in enumerate(queue)
    )

    await interaction.response.send_message(f"**Current Queue:**\n{queue_list}")


bot.run(TOKEN)