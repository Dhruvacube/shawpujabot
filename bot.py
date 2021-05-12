import os
from os.path import join
from pathlib import Path

import discord
import dotenv
from discord.ext import commands
from discord_slash import SlashCommand

dotenv_file = os.path.join(".env")
def token_get(tokenname):
    if os.path.isfile(dotenv_file):
        dotenv.load_dotenv(dotenv_file)
    return os.environ.get(tokenname, 'False').strip('\n')

bot = commands.Bot(command_prefix='s!',intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)

@bot.event
async def on_ready():
    cog_dir = Path(__file__).resolve(strict=True).parent / join('cogs')
    for filename in os.listdir(cog_dir):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')
    
    await bot.change_presence(status=discord.Status.idle, activity=discord.Activity(type=discord.ActivityType.watching, name='over Durga Puja'))
    print("Ready!")

bot.guild_ids = [836841841114480651] # Put your server ID in this array.

@slash.slash(name="ping", description="Get the Latency for the bot",guild_ids=bot.guild_ids)
async def _ping(ctx):
    await ctx.send(f"Pong! ({bot.latency*1000}ms)")

bot.run(token_get('BOT_TOKEN'))
