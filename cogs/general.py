from discord.ext import commands
from discord_slash import cog_ext


class General(commands.Cog):
    '''Some general required commands'''
    def __init__(self, bot):
        self.bot = bot
    
    @cog_ext.cog_slash(name="faq",description='Frequestly Asked Questions')
    async def faq(self, ctx):
        c = self.bot.get_channel(842021199390834728)
        await ctx.send(content=f"Please **check** {c.mention} channel")

def setup(bot):
    bot.add_cog(General(bot))
    