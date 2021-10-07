import datetime
from pathlib import Path

import discord
from discord.ext import commands


class BotEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_dir = Path(__file__).resolve().parent

    # on message event
    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.user.mentioned_in(message) and message.mention_everyone is False and message.content.lower() in ('<@!841956732506996756>', '<@841956732506996756>') or message.content.lower() in ('<@!840276343946215516> prefix', '<@840276343946215516> prefix'):
            if not message.author.bot:
                await message.channel.send('The prefix is **s!** ,A full list of all commands is available by typing ```s!help```')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 836841841114480651:
            channel = discord.utils.get(
                self.bot.get_all_channels(), id=836934061297106955)
            if member.bot:
                embed = discord.Embed(
                    title="Seems a new bot added",
                    description=f"<@&854764518316179466> please review this! Its urgent! Seems a new bot named {member.mention} entered! **Sus !**",
                    color=discord.Color.red()
                )
                await channel.send(f'<@&854764518316179466> or {member.guild.owner.mention}')
            else:
                embed = discord.Embed(
                    title="Welcome " + member.name + "!",
                    description=f"Please {member.mention} goto <#849951809195474966> and get your **updates roles**",
                    color=discord.Color.random(),
                    timestamp=datetime.datetime.utcnow(),
                )
                embed.set_image(url='https://i.imgur.com/mktY446.jpeg')
                embed.set_thumbnail(url='https://i.imgur.com/SizgkEZ.png')
                embed.set_author(name=self.bot.user.name,
                                icon_url=self.bot.user.avatar_url)
                embed.set_footer(text=f"Welcome {member.name}")
                await channel.send(member.mention)
            
            guild = member.guild

            if not member.bot:
                # Gets the member role as a `role` object
                role = discord.utils.get(
                    guild.roles, id=836985437738369094)
            else:
                role = discord.utils.get(
                    guild.roles, id=850355806926798909)
            await member.add_roles(role)  # Gives the role to the user
            await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(BotEvents(bot))
