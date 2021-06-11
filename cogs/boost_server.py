import discord
from discord.ext import commands
import random 

class BoostPlugin(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    
    @commands.is_owner()
    @commands.guild_only()
    @commands.command(name='nitro')
    async def send_nitro_boost_message(self, ctx,member: discord.Member):
        '''Send the nitro message to boosters channel'''
        embed = discord.Embed(
                title=f"**Nitro Boost**", 
                description=f"Thank you {member.mention} so much for **boosting** <a:nitro1:852813350545915905> !", 
                color=random.choice([
                    discord.Color.blurple(),
                    discord.Color.gold(),
                    discord.Color.dark_gold(),
                    discord.Color.purple()
                ])
            )
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/852813350545915905.gif?v=1')
        channel_message = self.bot.get_channel(852821942130180156)
        m = await channel_message.send(embed=embed)
        await m.add_reaction("<a:love_heart:852813348101816370>")
    
    @commands.is_owner()
    @commands.guild_only()
    @commands.command(name='levelup')
    async def send_nitro_level_message(self, ctx,level: int):
        '''Send the guild level up message in the channel'''
        if level not in (1,2,3):
            await ctx.send('Level must be from 1, 2, 3')
            return
        
        embed = discord.Embed(
                title=f"**Level {level} reached!**", 
                description=f"Thank you @everyone so much for **boosting** <a:nitro1:852813350545915905> We got to **Level {level} yaay! **!", 
                color=discord.Color.random()
            )
        if level==1:
            embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/627044920431214593.gif?v=1')
        elif level==2:
            embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/627044920431214593.gif?v=1')
        elif level==3:
            embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/627044920431214593.gif?v=1')
            
        channel_message = self.bot.get_channel(852821942130180156)
        m = await channel_message.send(embed=embed)
        await m.add_reaction("<a:love_heart:852813348101816370>")
    

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.type == discord.MessageType.premium_guild_subscription:
            try:
                desc = f"Thank you {message.author.mention} so much for **boosting** <a:nitro1:852813350545915905> !"
            except:
                desc = "Thank you so much for **boosting** <a:nitro1:852813350545915905> !"
            await message.add_reaction("<a:love_heart:852813348101816370>")
            channel_message = self.bot.get_channel(852821942130180156)
            
            #boost
            embed = discord.Embed(
                title=f"**Nitro Boost**", 
                description=desc, 
                color=random.choice([
                    discord.Color.blurple(),
                    discord.Color.gold(),
                    discord.Color.dark_gold(),
                    discord.Color.purple()
                ])
            )
            embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/852813350545915905.gif?v=1')
            m = await channel_message.send(embed=embed)
            await m.add_reaction("<a:love_heart:852813348101816370>")
        
        #level1
        if message.type == discord.MessageType.premium_guild_tier_1:
            await message.add_reaction("<a:love_heart:852813348101816370>")
            embed = discord.Embed(
                title=f"**Level 1 reached!**", 
                description=f"Thank you @everyone so much for **boosting** <a:nitro1:852813350545915905> We got to **Level 1 yaay! **!", 
                color=discord.Color.random()
            )
            embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/627044920431214593.gif?v=1')
            m = await channel_message.send(embed=embed)
            await m.add_reaction("<a:love_heart:852813348101816370>")
        
        #level2
        if message.type == discord.MessageType.premium_guild_tier_2:
            await message.add_reaction("<a:love_heart:852813348101816370>")
            embed = discord.Embed(
                title=f"**Level 2 reached!**", 
                description=f"Thank you @everyone so much for **boosting** <a:nitro1:852813350545915905> We got to **Level 2 yaay! **!", 
                color=discord.Color.random()
            )
            embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/852801854869340172.gif?v=1')
            m = await channel_message.send(embed=embed)
            await m.add_reaction("<a:love_heart:852813348101816370>")
        
        #level3
        if message.type == discord.MessageType.premium_guild_tier_3:
            await message.add_reaction("<a:love_heart:852813348101816370>")
            embed = discord.Embed(
                title=f"**Level 3 reached!**", 
                description=f"Thank you @everyone so much for **boosting** <a:nitro1:852813350545915905> We got to **Level 3 yaay! **!", 
                color=discord.Color.random()
            )
            embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/701335073387053106.gif?v=1')
            m = await channel_message.send(embed=embed)
            await m.add_reaction("<a:love_heart:852813348101816370>")
            
def setup(bot):
    bot.add_cog(BoostPlugin(bot))