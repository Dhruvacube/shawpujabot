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
    async def on_command_error(self, ctx, error):
        guild = ctx.guild
        if isinstance(error, commands.CommandOnCooldown):
            e1 = discord.Embed(
                title="Command Error!", description=f"`{error}`", color=discord.Color.random())
            e1.set_footer(text=f"{ctx.author.name}")
            await ctx.channel.send(embed=e1, delete_after=3)
        elif isinstance(error, commands.MissingPermissions):
            e3 = discord.Embed(
                title="Command Error!", description=f"`{error}`", color=discord.Color.random())
            e3.set_footer(text=f"{ctx.author.name}")
            await ctx.send(embed=e3, delete_after=3)
        elif isinstance(error, commands.MissingRequiredArgument):
            e4 = discord.Embed(
                title="Command Error!", description=f"`{error}`", color=discord.Color.random())
            e4.set_footer(text=f"{ctx.author.name}")
            await ctx.channel.send(embed=e4, delete_after=2)
        elif isinstance(error, commands.CommandNotFound):
            e2 = discord.Embed(
                title="Command Error!", description=f"`{error}`", color=discord.Color.random())
            e2.set_footer(text=f"{ctx.author.name}")
            await ctx.channel.send(embed=e2, delete_after=3)
        elif isinstance(error, commands.NotOwner):
            await ctx.send("Only the bot owner may execute this command.")

        elif isinstance(error, commands.CommandInvokeError):
            e7 = discord.Embed(title="Oh no, I guess I have not been given proper access! Or some internal error",
                               description=f"`{error}`", color=discord.Color.random())
            e7.add_field(name="Command Error Caused By:",
                         value=f"{ctx.command}")
            e7.add_field(name="By", value=f"{ctx.author.name}")
            e7.set_footer(text=f"{ctx.author.name}")
            await ctx.channel.send(embed=e7, delete_after=5)
        else:
            haaha = ctx.author.avatar_url
            e9 = discord.Embed(title="Oh no there was some error",
                               description=f"`{error}`", color=discord.Color.random())
            e9.add_field(name="**Command Error Caused By**",
                         value=f"{ctx.command}")
            e9.add_field(
                name="**By**", value=f"**ID** : {ctx.author.id}, **Name** : {ctx.author.name}")
            e9.set_thumbnail(url=f"{haaha}")
            e9.set_footer(text=f"{ctx.author.name}")
            await ctx.channel.send(embed=e9, delete_after=2)
            await ctx.send('**Error report was successfully sent**', delete_after=2)


def setup(bot):
    bot.add_cog(BotEvents(bot))