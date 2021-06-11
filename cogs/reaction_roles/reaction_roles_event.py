import asyncio
import datetime
from pathlib import Path

import discord
from discord.ext import commands, tasks


class Locks:
    def __init__(self):
        self.locks = {}
        self.main_lock = asyncio.Lock()

    async def get_lock(self, user_id):
        async with self.main_lock:
            if not user_id in self.locks:
                self.locks[user_id] = asyncio.Lock()

            return self.locks[user_id]


lock_manager = Locks()


class ReactionRolesEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.base_dir = Path(__file__).resolve().parent
    
    async def getchannel(self, channel_id):
        channel = self.bot.get_channel(channel_id)

        if not channel:
            channel = await self.bot.fetch_channel(channel_id)

        return channel

    async def getguild(self, guild_id):
        guild = self.bot.get_guild(guild_id)

        if not guild:
            guild = await self.bot.fetch_guild(guild_id)

        return guild

    @commands.Cog.listener()
    async def on_ready(self):
        print("Reaction Light ready!")
        self.cleandb.start()
        self.check_cleanup_queued_guilds.start()

    @tasks.loop(hours=6)
    async def check_cleanup_queued_guilds(self):
        cleanup_guild_ids = self.db.fetch_cleanup_guilds(guild_ids_only=True)
        for guild_id in cleanup_guild_ids:
            try:
                await self.bot.fetch_guild(guild_id)
                self.db.remove_cleanup_guild(guild_id)

            except discord.Forbidden:
                continue

    async def system_notification(self, guild_id, text, embed=None):
        # Send a message to the system channel (if set)
        system_channel1 = await self.getguild(guild_id)
        system_channel = system_channel1.system_channel
        if guild_id:
            server_channel = self.db.fetch_systemchannel(guild_id)

            if isinstance(server_channel, Exception):
                await self.system_notification(
                    None,
                    "Database error when fetching guild system"
                    f" channels:\n```\n{server_channel}\n```\n\n{text}",
                )
                return

            if server_channel:
                server_channel = server_channel[0][0]

            if server_channel:
                try:
                    target_channel = await self.getchannel(server_channel)
                    if embed:
                        await target_channel.send(text, embed=embed)
                    else:
                        await target_channel.send(text)

                except discord.Forbidden:
                    await self.system_notification(None, text)

            else:
                if embed:
                    await self.system_notification(None, text, embed=embed)
                else:
                    await self.system_notification(None, text)

        elif system_channel:
            try:
                target_channel = await self.getchannel(system_channel)
                if embed:
                    await target_channel.send(text, embed=embed)
                else:
                    await target_channel.send(text)

            except discord.NotFound:
                print("I cannot find the system channel.")

            except discord.Forbidden:
                print("I cannot send messages to the system channel.")

        else:
            print(text)

    @tasks.loop(hours=24)
    async def cleandb(self):
        # Cleans the database by deleting rows of reaction role messages that don't exist anymore
        messages = self.db.fetch_all_messages()
        guilds = self.db.fetch_all_guilds()
        # Get the cleanup queued guilds
        cleanup_guild_ids = self.db.fetch_cleanup_guilds(guild_ids_only=True)

        if isinstance(messages, Exception):
            await self.system_notification(
                None,
                "Database error when fetching messages during database"
                f" cleaning:\n```\n{messages}\n```",
            )
            return

        for message in messages:
            try:
                channel_id = message[1]
                channel = await self.bot.fetch_channel(channel_id)

                await channel.fetch_message(message[0])

            except discord.NotFound as e:
                # If unknown channel or unknown message
                if e.code == 10003 or e.code == 10008:
                    delete = self.db.delete(message[0], message[3])

                    if isinstance(delete, Exception):
                        await self.system_notification(
                            channel.guild.id,
                            "Database error when deleting messages during database"
                            f" cleaning:\n```\n{delete}\n```",
                        )
                        return

                    await self.system_notification(
                        channel.guild.id,
                        "I deleted the database entries of a message that was removed."
                        f"\n\nID: {message} in {channel.mention}",
                    )

            except discord.Forbidden:
                # If we can't fetch the channel due to the bot not being in the guild or permissions we usually cant mention it or get the guilds id using the channels object
                await self.system_notification(
                    message[3],
                    "I do not have access to a message I have created anymore. "
                    "I cannot manage the roles of users reacting to it."
                    f"\n\nID: {message[0]} in channel {message[1]}",
                )

        if isinstance(guilds, Exception):
            await self.system_notification(
                None,
                "Database error when fetching guilds during database"
                f" cleaning:\n```\n{guilds}\n```",
            )
            return

        for guild_id in guilds:
            try:
                await self.bot.fetch_guild(guild_id)
                if guild_id in cleanup_guild_ids:
                    self.db.remove_cleanup_guild(guild_id)

            except discord.Forbidden:
                # If unknown guild
                if guild_id in cleanup_guild_ids:
                    continue
                else:
                    self.db.add_cleanup_guild(
                        guild_id, round(datetime.datetime.utcnow().timestamp())
                    )

        cleanup_guilds = self.db.fetch_cleanup_guilds()

        if isinstance(cleanup_guilds, Exception):
            await self.system_notification(
                None,
                "Database error when fetching cleanup guilds during"
                f" cleaning:\n```\n{cleanup_guilds}\n```",
            )
            return

        current_timestamp = round(datetime.datetime.utcnow().timestamp())
        for guild in cleanup_guilds:
            if int(guild[1]) - current_timestamp <= -86400:
                # The guild has been invalid / unreachable for more than 24 hrs, try one more fetch then give up and purge the guilds database entries
                try:
                    await self.bot.fetch_guild(guild[0])
                    self.db.remove_cleanup_guild(guild[0])
                    continue

                except discord.Forbidden:
                    delete = self.db.remove_guild(guild[0])
                    delete2 = self.db.remove_cleanup_guild(guild[0])
                    if isinstance(delete, Exception):
                        await self.system_notification(
                            None,
                            "Database error when deleting a guilds datebase entries during"
                            f" database cleaning:\n```\n{delete}\n```",
                        )
                        return

                    elif isinstance(delete2, Exception):
                        await self.system_notification(
                            None,
                            "Database error when deleting a guilds datebase entries during"
                            f" database cleaning:\n```\n{delete2}\n```",
                        )
                        return

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.db.remove_guild(guild.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        reaction = str(payload.emoji)
        msg_id = payload.message_id
        ch_id = payload.channel_id
        user_id = payload.user_id
        guild_id = payload.guild_id
        exists = self.db.exists(msg_id)

        async with await lock_manager.get_lock(user_id):
            if isinstance(exists, Exception):
                await self.system_notification(
                    guild_id,
                    f"Database error after a user added a reaction:\n```\n{exists}\n```",
                )

            elif exists:
                # Checks that the message that was reacted to is a reaction-role message managed by the bot
                reactions = self.db.get_reactions(msg_id)

                if isinstance(reactions, Exception):
                    await self.system_notification(
                        guild_id,
                        f"Database error when getting reactions:\n```\n{reactions}\n```",
                    )
                    return

                ch = self.bot.get_channel(ch_id)
                msg = await ch.fetch_message(msg_id)
                user = self.bot.get_user(user_id)
                if reaction not in reactions:
                    # Removes reactions added to the reaction-role message that are not connected to any role
                    await msg.remove_reaction(reaction, user)

                else:
                    # Gives role if it has permissions, else 403 error is raised
                    role_id = reactions[reaction]
                    server = await self.getguild(guild_id)
                    member = server.get_member(user_id)
                    role = discord.utils.get(server.roles, id=role_id)
                    if user_id != self.bot.user.id:
                        unique = self.db.isunique(msg_id)
                        if unique:
                            for existing_reaction in msg.reactions:
                                if str(existing_reaction.emoji) == reaction:
                                    continue
                                async for reaction_user in existing_reaction.users():
                                    if reaction_user.id == user_id:
                                        await msg.remove_reaction(existing_reaction, user)
                                        # We can safely break since a user can only have one reaction at once
                                        break

                        try:
                            await member.add_roles(role)
                            notify = self.db.notify(guild_id)
                            if isinstance(notify, Exception):
                                await self.system_notification(
                                    guild_id,
                                    f"Database error when checking if role notifications are turned on:\n```\n{notify}\n```",
                                )
                                return

                            if notify:
                                await user.send(
                                    f"You now have the following role: **{role.name}**"
                                )

                        except discord.Forbidden:
                            await self.system_notification(
                                guild_id,
                                "Someone tried to add a role to themselves but I do not have"
                                " permissions to add it. Ensure that I have a role that is"
                                " hierarchically higher than the role I have to assign, and"
                                " that I have the `Manage Roles` permission.",
                            )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        reaction = str(payload.emoji)
        msg_id = payload.message_id
        user_id = payload.user_id
        guild_id = payload.guild_id
        exists = self.db.exists(msg_id)

        if isinstance(exists, Exception):
            await self.system_notification(
                guild_id,
                f"Database error after a user removed a reaction:\n```\n{exists}\n```",
            )

        elif exists:
            # Checks that the message that was unreacted to is a reaction-role message managed by the bot
            reactions = self.db.get_reactions(msg_id)

            if isinstance(reactions, Exception):
                await self.system_notification(
                    guild_id,
                    f"Database error when getting reactions:\n```\n{reactions}\n```",
                )

            elif reaction in reactions:
                role_id = reactions[reaction]
                # Removes role if it has permissions, else 403 error is raised
                server = await self.getguild(guild_id)
                member = server.get_member(user_id)

                if not member:
                    member = await server.fetch_member(user_id)

                role = discord.utils.get(server.roles, id=role_id)
                try:
                    await member.remove_roles(role)
                    notify = self.db.notify(guild_id)
                    if isinstance(notify, Exception):
                        await self.system_notification(
                            guild_id,
                            f"Database error when checking if role notifications are turned on:\n```\n{notify}\n```",
                        )
                        return

                    if notify:
                        await member.send(
                            f"You do not have the following role anymore: **{role.name}**"
                        )

                except discord.Forbidden:
                    await self.system_notification(
                        guild_id,
                        "Someone tried to remove a role from themselves but I do not have"
                        " permissions to remove it. Ensure that I have a role that is"
                        " hierarchically higher than the role I have to remove, and that I"
                        " have the `Manage Roles` permission.",
                    )


def setup(bot):
    bot.add_cog(ReactionRolesEvents(bot))
