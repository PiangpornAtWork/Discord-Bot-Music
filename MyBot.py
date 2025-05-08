import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("SERVER_ID")
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
    # await bot.tree.sync()
    # print(f"{bot.user} is online!")

# @bot.event
# async def on_message(msg):
#     if msg.author.id != bot.user.id:
#         await msg.channel.send(f"interesting message, {msg.author.mention}")

@bot.tree.command(name='greet', description="Send a greeting to the user", guild=discord.Object(id=SERVER_ID))
async def greet(interaction: discord.Interaction):
    username = interaction.user.mention
    await interaction.response.send_message(f"Hello there, {username}")

@bot.tree.command(name='play', description="Paly a song or add it to the queue", guild=discord.Object(id=SERVER_ID))
@app_commands.describe(song_query="Search query")
async def play(interaction: discord.Interaction, song_query:str):
    username = interaction.user.mention
    await interaction.response.send_message(f"Hello there, {username}")


bot.run(TOKEN)