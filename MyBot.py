import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp
import asyncio
from collections import deque



load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = "788391906048606228"
SONG_QUEUES={}

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



@bot.tree.command(name='greet', description="Send a greeting to the user", guild=discord.Object(id=SERVER_ID))
async def greet(interaction: discord.Interaction):
    username = interaction.user.mention
    await interaction.response.send_message(f"Hello there, {username}")




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

    query = "ytsearch1: " + song_query
    results = await search_ytdlp_async(query, ydl_options)
    tracks = results.get("entries", [])

    if tracks is None:
        await interaction.followup.send("No results found.")
        return

    first_track = tracks[0]
    audio_url = first_track["url"]
    title = first_track.get("title", "Untitled")

    guild_id = str(interaction.guild_id)
    if SONG_QUEUES.get(guild_id) is None:
        SONG_QUEUES[guild_id] = deque()

    SONG_QUEUES[guild_id].append((audio_url, title))
    print(f"url : {audio_url}")
    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(f"Added to queue: **{title}**")
    else:
        await interaction.followup.send(f"Now playing: **{title}**")
        await play_next_song(voice_client, guild_id, interaction.channel)


async def play_next_song(voice_client, guild_id, channel):
    if SONG_QUEUES[guild_id]:
        audio_url, title = SONG_QUEUES[guild_id].popleft()

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn -c:a libopus -b:a 128k",
        }

        source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg.exe")

        def after_play(error):
            if error:
                print(f"Error playing {title}: {error}")
            asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)

        voice_client.play(source, after=after_play)
        asyncio.create_task(channel.send(f"Now playing: **{title}**"))
    else:
        await voice_client.disconnect()
        SONG_QUEUES[guild_id] = deque()



bot.run(TOKEN)