import os
from os.path import join
from pathlib import Path

import discord
import dotenv
from discord.ext import commands
from pretty_help import PrettyHelp

from core import database, schema

dotenv_file = os.path.join(".env")


def token_get(tokenname):
    if os.path.isfile(dotenv_file):
        dotenv.load_dotenv(dotenv_file)
    return os.environ.get(tokenname, 'False').strip('\n')


intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.messages = True
intents.emojis = True

bot = commands.Bot(
    command_prefix='s!',
    intents=intents,
    help_command=PrettyHelp(show_index=True),
    allowed_mentions=discord.AllowedMentions(
        users=True,
        roles=False,
        everyone=False
    ),
    case_insensitive=True,
    strip_after_prefix=True,
    owner_ids = set([571889108046184449, 747729781369602049])
)

directory = os.path.dirname(os.path.realpath(__file__))
bot.db_file = f"{directory}/reactionlight.db"
bot.db = database.Database(bot.db_file)


cog_dir = Path(__file__).resolve(strict=True).parent / join('cogs')
for filename in os.listdir(cog_dir):
    if os.path.isdir(cog_dir / filename) and filename != 'util':
        for i in os.listdir(cog_dir / filename):
            if i.endswith('.py'):
                bot.load_extension(f'cogs.{filename.strip(" ")}.{i[:-3]}')
    else:
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')


async def database_updates():
    handler = schema.SchemaHandler(bot.db_file, bot)
    if handler.version == 0:
        handler.zero_to_one()
        messages = bot.db.fetch_all_messages()
        for message in messages:
            channel_id = message[1]
            channel = bot.get_channel(channel_id)
            bot.db.add_guild(channel.id, channel.guild.id)

    if handler.version == 1:
        handler.one_to_two()

    if handler.version == 2:
        handler.two_to_three()


@bot.event
async def on_ready():
    await database_updates()
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name='over Durga Puja'
        )
    )
    print("Ready!")


try:
    bot.run(token_get('BOT_TOKEN'))
except discord.PrivilegedIntentsRequired:
    print(
        "[Login Failure] You need to enable the server members intent on the Discord Developers Portal."
    )
except discord.errors.LoginFailure:
    print("[Login Failure] The token inserted in config.ini is invalid.")
