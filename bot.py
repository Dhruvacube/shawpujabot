import ast
import logging
import os
import time
from os.path import join
import datetime
from pathlib import Path

import discord
import dotenv
from lib import (PaginatedHelpCommand)
from discord.ext import commands

from core import database, schema

log = logging.getLogger(__name__)

dotenv_file = os.path.join(".env")
def token_get(tokenname):
    if os.path.isfile(dotenv_file):
        dotenv.load_dotenv(dotenv_file)
    return os.environ.get(tokenname, 'False').strip('\n')

def format_dt(dt, style=None):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'

async def database_updates(bot):
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


def get_prefix(bot, message):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""
    prefixes = ['s!', '?', 's?']
    return commands.when_mentioned_or(*prefixes)(bot, message)

class AnbuBot(commands.AutoShardedBot):
    def __init__(self):
        directory = os.path.dirname(os.path.realpath(__file__))
        self.db_file = f"{directory}/reactionlight.db"
        self.db = database.Database(self.db_file)
        allowed_mentions = discord.AllowedMentions(
            roles=True, 
            everyone=True, 
            users=True
        )
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            voice_states=True,
            messages=True,
            reactions=True,
        ).all()
        self._cache = {}

        self.version = str(token_get('BOT_VER'))

        self.start_time = discord.utils.utcnow()

        self.uptime = format_dt(self.start_time,'R')
        
        super().__init__(
            command_prefix=get_prefix,
            chunk_guilds_at_startup=False,
            heartbeat_timeout=150.0,
            pm_help=None,
            help_attrs=dict(hidden=True),
            allowed_mentions=allowed_mentions,
            intents=intents,
            enable_debug_events=True,
            help_command=PaginatedHelpCommand(),
            owner_ids = set([571889108046184449, 747729781369602049])
        )
    
    def run(self):
        try:     
            log.info('Bot will now start')
            super().run(token_get('BOT_TOKEN'), reconnect=True)
        except discord.PrivilegedIntentsRequired:
            log.critical(
                "[Login Failure] You need to enable the server members intent on the Discord Developers Portal."
            )
        except discord.errors.LoginFailure:
            log.critical("[Login Failure] The token initialsed in environment(or .env file) is invalid.")
        except KeyboardInterrupt:
            log.critical('The bot is shutting down since force shutdown was initiated.')
        except Exception as e:
            log.critical('An exception occured, %s', e)
    
    
    async def on_ready(self):
        await database_updates(self)
        cog_dir = Path(__file__).resolve(strict=True).parent / join('cogs')
        for filename in os.listdir(cog_dir):
            if os.path.isdir(cog_dir / filename) and filename != 'util':
                for i in os.listdir(cog_dir / filename):
                    if i.endswith('.py'):
                        self.load_extension(f'cogs.{filename.strip(" ")}.{i[:-3]}')
            else:
                if filename.endswith('.py'):
                    self.load_extension(f'cogs.{filename[:-3]}')
        await self.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name='over Durga Puja'
            )
        )
        log.critical("Ready!")

if __name__ == "__main__":
    AnbuBot().run()
