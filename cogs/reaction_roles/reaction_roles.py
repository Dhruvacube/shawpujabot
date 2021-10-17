import asyncio

import discord
from discord.ext import commands, tasks

from core import database, schema


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prefix = "s!"
        self.db = bot.db
        self.description = "Create reaction roles"

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\U000023f9\U0000fe0f")

    def isadmin(self, member, guild_id):
        # Checks if command author has an admin role that was added with rl!admin
        admins = self.db.get_admins(guild_id)

        if isinstance(admins, Exception):
            print(f"Error when checking if the member is an admin:\n{admins}")
            return False

        try:
            member_roles = [role.id for role in member.roles]
            return [admin_role for admin_role in admins if admin_role in member_roles]

        except AttributeError:
            # Error raised from 'fake' users, such as webhooks
            return False

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

    async def getuser(self, user_id):
        user = self.bot.get_user(user_id)

        if not user:
            user = await self.bot.fetch_user(user_id)

        return user

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

    async def formatted_channel_list(self, channel):
        all_messages = self.db.fetch_messages(channel.id)
        if isinstance(all_messages, Exception):
            await self.system_notification(
                channel.guild.id,
                f"Database error when fetching messages:\n```\n{all_messages}\n```",
            )
            return

        formatted_list = []
        counter = 1
        for msg_id in all_messages:
            try:
                old_msg = await channel.fetch_message(int(msg_id))

            except discord.NotFound:
                # Skipping reaction-role messages that might have been deleted without updating CSVs
                continue

            except discord.Forbidden:
                await self.system_notification(
                    channel.guild.id,
                    "I do not have permissions to edit a reaction-role message"
                    f" that I previously created.\n\nID: {msg_id} in"
                    f" {channel.mention}",
                )
                continue

            entry = (
                f"`{counter}`"
                f" {old_msg.embeds[0].title if old_msg.embeds else old_msg.content}"
            )
            formatted_list.append(entry)
            counter += 1

        return formatted_list

    @commands.command(name="new", aliases=["create"])
    async def new(self, ctx):
        """Create a new reaction"""
        if self.isadmin(ctx.message.author, ctx.guild.id):
            sent_initial_message = await ctx.send(
                "Welcome to the Reaction Light creation program. Please provide the required information once requested. If you would like to abort the creation, do not respond and the program will time out."
            )
            rl_object = {}
            cancelled = False

            def check(message):
                return (
                    message.author.id == ctx.message.author.id and message.content != ""
                )

            if not cancelled:
                error_messages = []
                user_messages = []
                sent_reactions_message = await ctx.send(
                    "Attach roles and emojis separated by one space (one combination"
                    " per message). When you are done type `done`. Example:\n:smile:"
                    " `@Role`"
                )
                rl_object["reactions"] = {}
                try:
                    while True:
                        reactions_message = await self.bot.wait_for(
                            "message", timeout=120, check=check
                        )
                        user_messages.append(reactions_message)
                        if reactions_message.content.lower() != "done":
                            reaction = (reactions_message.content.split())[0]
                            try:
                                role = reactions_message.role_mentions[0].id
                            except IndexError:
                                error_messages.append(
                                    (
                                        await ctx.send(
                                            "Mention a role after the reaction. Example:\n:smile:"
                                            " `@Role`"
                                        )
                                    )
                                )
                                continue

                            if reaction in rl_object["reactions"]:
                                error_messages.append(
                                    (
                                        await ctx.send(
                                            "You have already used that reaction for another role. Please choose another reaction"
                                        )
                                    )
                                )
                                continue
                            else:
                                try:
                                    await reactions_message.add_reaction(reaction)
                                    rl_object["reactions"][reaction] = role
                                except discord.HTTPException:
                                    error_messages.append(
                                        (
                                            await ctx.send(
                                                "You can only use reactions uploaded to servers the bot has"
                                                " access to or standard emojis."
                                            )
                                        )
                                    )
                                    continue
                        else:
                            break
                except asyncio.TimeoutError:
                    await ctx.author.send(
                        "Reaction Light creation failed, you took too long to provide the requested information."
                    )
                    cancelled = True
                finally:
                    await sent_reactions_message.delete()
                    for message in error_messages + user_messages:
                        await message.delete()

            if not cancelled:
                sent_limited_message = await ctx.send(
                    "Would you like to limit users to select only have one of the roles at a given time? Please react with a 🔒 to limit users or with a ♾️ to allow users to select multiple roles."
                )

                def reaction_check(payload):
                    return (
                        payload.member.id == ctx.message.author.id
                        and payload.message_id == sent_limited_message.id
                        and (str(payload.emoji) == "🔒" or str(payload.emoji) == "♾️")
                    )

                try:
                    await sent_limited_message.add_reaction("🔒")
                    await sent_limited_message.add_reaction("♾️")
                    limited_message_response_payload = await self.bot.wait_for(
                        "raw_reaction_add", timeout=120, check=reaction_check
                    )

                    if str(limited_message_response_payload.emoji) == "🔒":
                        rl_object["limit_to_one"] = 1
                    else:
                        rl_object["limit_to_one"] = 0
                except asyncio.TimeoutError:
                    await ctx.author.send(
                        "Reaction Light creation failed, you took too long to provide the requested information."
                    )
                    cancelled = True
                finally:
                    await sent_limited_message.delete()

            if not cancelled:
                sent_oldmessagequestion_message = await ctx.send(
                    f"Would you like to use an existing message or create one using {self.bot.user.mention}? Please react with a 🗨️ to use an existing message or a 🤖 to create one."
                )

                def reaction_check2(payload):
                    return (
                        payload.member.id == ctx.message.author.id
                        and payload.message_id == sent_oldmessagequestion_message.id
                        and (str(payload.emoji) == "🗨️" or str(payload.emoji) == "🤖")
                    )

                try:
                    await sent_oldmessagequestion_message.add_reaction("🗨️")
                    await sent_oldmessagequestion_message.add_reaction("🤖")
                    oldmessagequestion_response_payload = await self.bot.wait_for(
                        "raw_reaction_add", timeout=120, check=reaction_check2
                    )

                    if str(oldmessagequestion_response_payload.emoji) == "🗨️":
                        rl_object["old_message"] = True
                    else:
                        rl_object["old_message"] = False
                except asyncio.TimeoutError:
                    await ctx.author.send(
                        "Reaction Light creation failed, you took too long to provide the requested information."
                    )
                    cancelled = True
                finally:
                    await sent_oldmessagequestion_message.delete()

            if not cancelled:
                error_messages = []
                user_messages = []
                if rl_object["old_message"]:
                    sent_oldmessage_message = await ctx.send(
                        "Which message would you like to use? Please react with a 🔧 on the message you would like to use."
                    )

                    def reaction_check3(payload):
                        return (
                            payload.member.id == ctx.message.author.id
                            and payload.guild_id == sent_oldmessage_message.guild.id
                            and str(payload.emoji) == "🔧"
                        )

                    try:
                        while True:
                            oldmessage_response_payload = await self.bot.wait_for(
                                "raw_reaction_add", timeout=120, check=reaction_check3
                            )
                            try:
                                try:
                                    channel = await self.getchannel(
                                        oldmessage_response_payload.channel_id
                                    )
                                except discord.InvalidData:
                                    channel = None
                                except discord.HTTPException:
                                    channel = None

                                if channel is None:
                                    raise discord.NotFound
                                try:
                                    message = await channel.fetch_message(
                                        oldmessage_response_payload.message_id
                                    )
                                except discord.HTTPException:
                                    raise discord.NotFound
                                try:
                                    await message.add_reaction("👌")
                                    await message.remove_reaction("👌", message.guild.me)
                                    await message.remove_reaction("🔧", ctx.author)
                                except discord.HTTPException:
                                    raise discord.NotFound
                                if self.db.exists(message.id):
                                    raise ValueError
                                rl_object["message"] = dict(
                                    message_id=message.id,
                                    channel_id=message.channel.id,
                                    guild_id=message.guild.id,
                                )
                                final_message = message
                                break
                            except discord.NotFound:
                                error_messages.append(
                                    (
                                        await ctx.send(
                                            "I can not access or add reactions to the requested message. Do I have sufficent permissions?"
                                        )
                                    )
                                )
                            except ValueError:
                                error_messages.append(
                                    (
                                        await ctx.send(
                                            f"This message already got a reaction light instance attached to it, consider running `{self.prefix}edit` instead."
                                        )
                                    )
                                )
                    except asyncio.TimeoutError:
                        await ctx.author.send(
                            "Reaction Light creation failed, you took too long to provide the requested information."
                        )
                        cancelled = True
                    finally:
                        await sent_oldmessage_message.delete()
                        for message in error_messages:
                            await message.delete()
                else:
                    sent_channel_message = await ctx.send(
                        "Mention the #channel where to send the auto-role message."
                    )
                    try:
                        while True:
                            channel_message = await self.bot.wait_for(
                                "message", timeout=120, check=check
                            )
                            if channel_message.channel_mentions:
                                rl_object[
                                    "target_channel"
                                ] = channel_message.channel_mentions[0]
                                break
                            else:
                                error_messages.append(
                                    (
                                        await message.channel.send(
                                            "The channel you mentioned is invalid."
                                        )
                                    )
                                )
                    except asyncio.TimeoutError:
                        await ctx.author.send(
                            "Reaction Light creation failed, you took too long to provide the requested information."
                        )
                        cancelled = True
                    finally:
                        await sent_channel_message.delete()
                        for message in error_messages:
                            await message.delete()

            if not cancelled and "target_channel" in rl_object:
                error_messages = []
                selector_embed = discord.Embed(
                    title="Embed_title",
                    description="Embed_content",
                    colour=discord.Color.random(),
                )
                selector_embed.set_footer(
                    text=f"{self.bot.user.name}", icon_url=self.bot.user.avatar_url
                )

                sent_message_message = await message.channel.send(
                    "What would you like the message to say?\nFormatting is:"
                    " `Message // Embed_title // Embed_content`.\n\n`Embed_title`"
                    " and `Embed_content` are optional. You can type `none` in any"
                    " of the argument fields above (e.g. `Embed_title`) to make the"
                    " bot ignore it.\n\n\nMessage",
                    embed=selector_embed,
                )
                try:
                    while True:
                        message_message = await self.bot.wait_for(
                            "message", timeout=120, check=check
                        )
                        # I would usually end up deleting message_message in the end but users usually want to be able to access the
                        # format they once used incase they want to make any minor changes
                        msg_values = message_message.content.split(" // ")
                        # This whole system could also be re-done using wait_for to make the syntax easier for the user
                        # But it would be a breaking change that would be annoying for thoose who have saved their message commands
                        # for editing.
                        selector_msg_body = (
                            msg_values[0] if msg_values[0].lower(
                            ) != "none" else None
                        )
                        selector_embed = discord.Embed(
                            colour=discord.Color.random())
                        selector_embed.set_footer(
                            text=f"{self.bot.user.name}",
                            icon_url=self.bot.user.avatar_url,
                        )

                        if len(msg_values) > 1:
                            if msg_values[1].lower() != "none":
                                selector_embed.title = msg_values[1]
                            if len(msg_values) > 2 and msg_values[2].lower() != "none":
                                selector_embed.description = msg_values[2]

                        # Prevent sending an empty embed instead of removing it
                        selector_embed = (
                            selector_embed
                            if selector_embed.title or selector_embed.description
                            else None
                        )

                        if selector_msg_body or selector_embed:
                            target_channel = rl_object["target_channel"]
                            sent_final_message = None
                            try:
                                sent_final_message = await target_channel.send(
                                    content=selector_msg_body, embed=selector_embed
                                )
                                rl_object["message"] = dict(
                                    message_id=sent_final_message.id,
                                    channel_id=sent_final_message.channel.id,
                                    guild_id=sent_final_message.guild.id,
                                )
                                final_message = sent_final_message
                                break
                            except discord.Forbidden:
                                error_messages.append(
                                    (
                                        await message.channel.send(
                                            "I don't have permission to send messages to"
                                            f" the channel {target_channel.mention}. Please check my permissions and try again."
                                        )
                                    )
                                )
                except asyncio.TimeoutError:
                    await ctx.author.send(
                        "Reaction Light creation failed, you took too long to provide the requested information."
                    )
                    cancelled = True
                finally:
                    await sent_message_message.delete()
                    for message in error_messages:
                        await message.delete()

            if not cancelled:
                # Ait we are (almost) all done, now we just need to insert that into the database and add the reactions 💪
                try:
                    r = self.db.add_reaction_role(rl_object)
                except database.DuplicateInstance:
                    await ctx.send(
                        f"The requested message already got a reaction light instance attached to it, consider running `{self.prefix}edit` instead."
                    )
                    return

                if isinstance(r, Exception):
                    await self.system_notification(
                        ctx.message.guild.id,
                        f"Database error when creating reaction-light instance:\n```\n{r}\n```",
                    )
                    return
                for reaction, _ in rl_object["reactions"].items():
                    await final_message.add_reaction(reaction)
                await ctx.message.add_reaction("✅")
            await sent_initial_message.delete()

            if not cancelled:
                await ctx.message.add_reaction("❌")
        else:
            await ctx.send(
                f"You do not have an admin role. You might want to use `{self.prefix}admin`"
                " first."
            )

    @commands.command(name="edit")
    async def edit_selector(self, ctx):
        """edits the text and embed of an existing reaction role message."""
        if self.isadmin(ctx.message.author, ctx.guild.id):
            # Reminds user of formatting if it is wrong
            msg_values = ctx.message.content.split()
            if len(msg_values) < 2:
                await ctx.send(
                    f"**Type** `{self.prefix}edit #channelname` to get started. Replace"
                    " `#channelname` with the channel where the reaction-role message you"
                    " wish to edit is located."
                )
                return

            elif len(msg_values) == 2:
                try:
                    channel_id = ctx.message.channel_mentions[0].id

                except IndexError:
                    await ctx.send("You need to mention a channel.")
                    return

                channel = await self.getchannel(channel_id)
                all_messages = await self.formatted_channel_list(channel)
                if len(all_messages) == 1:
                    await ctx.send(
                        "There is only one reaction-role message in this channel."
                        f" **Type**:\n```\n{self.prefix}edit #{channel.name} // 1 // New Message"
                        " // New Embed Title (Optional) // New Embed Description"
                        " (Optional)\n```\nto edit the reaction-role message. You can type"
                        " `none` in any of the argument fields above (e.g. `New Message`)"
                        " to make the bot ignore it."
                    )

                elif len(all_messages) > 1:
                    await ctx.send(
                        f"There are **{len(all_messages)}** reaction-role messages in this"
                        f" channel. **Type**:\n```\n{self.prefix}edit #{channel.name} //"
                        " MESSAGE_NUMBER // New Message // New Embed Title (Optional) //"
                        " New Embed Description (Optional)\n```\nto edit the desired one."
                        " You can type `none` in any of the argument fields above (e.g."
                        " `New Message`) to make the bot ignore it. The list of the"
                        " current reaction-role messages is:\n\n"
                        + "\n".join(all_messages)
                    )

                else:
                    await ctx.send(
                        "There are no reaction-role messages in that channel."
                    )

            elif len(msg_values) > 2:
                try:
                    # Tries to edit the reaction-role message
                    # Raises errors if the channel sent was invalid or if the bot cannot edit the message
                    channel_id = ctx.message.channel_mentions[0].id
                    channel = await self.getchannel(channel_id)
                    msg_values = ctx.message.content.split(" // ")
                    selector_msg_number = msg_values[1]
                    all_messages = self.db.fetch_messages(channel_id)

                    if isinstance(all_messages, Exception):
                        await self.system_notification(
                            ctx.message.guild.id,
                            "Database error when fetching"
                            f" messages:\n```\n{all_messages}\n```",
                        )
                        return

                    counter = 1
                    if all_messages:
                        message_to_edit_id = None
                        for msg_id in all_messages:
                            # Loop through all msg_ids and stops when the counter matches the user input
                            if str(counter) == selector_msg_number:
                                message_to_edit_id = msg_id
                                break

                            counter += 1

                    else:
                        await ctx.send(
                            "You selected a reaction-role message that does not exist."
                        )
                        return

                    if message_to_edit_id:
                        old_msg = await channel.fetch_message(int(message_to_edit_id))

                    else:
                        await ctx.send(
                            "Select a valid reaction-role message number (i.e. the number"
                            " to the left of the reaction-role message content in the list"
                            " above)."
                        )
                        return
                    await old_msg.edit(suppress=False)
                    selector_msg_new_body = (
                        msg_values[2] if msg_values[2].lower(
                        ) != "none" else None
                    )
                    selector_embed = discord.Embed()

                    if len(msg_values) > 3 and msg_values[3].lower() != "none":
                        selector_embed.title = msg_values[3]
                        selector_embed.colour = discord.Color.random()
                        selector_embed.set_footer(
                            text=f"{self.bot.user.name}",
                            icon_url=self.bot.user.avatar_url,
                        )

                    if len(msg_values) > 4 and msg_values[4].lower() != "none":
                        selector_embed.description = msg_values[4]
                        selector_embed.colour = discord.Color.random()
                        selector_embed.set_footer(
                            text=f"{self.bot.user.name}",
                            icon_url=self.bot.user.avatar_url,
                        )

                    try:
                        if selector_embed.title or selector_embed.description:
                            await old_msg.edit(
                                content=selector_msg_new_body, embed=selector_embed
                            )

                        else:
                            await old_msg.edit(
                                content=selector_msg_new_body, embed=None
                            )

                        await ctx.send("Message edited.")
                    except discord.Forbidden:
                        await ctx.send(
                            "I can only edit messages that are created by me, please edit the message in some other way."
                        )
                        return
                    except discord.HTTPException as e:
                        if e.code == 50006:
                            await ctx.send(
                                "You can't use an empty message as role-reaction message."
                            )

                        else:
                            guild_id = ctx.message.guild.id
                            await self.system_notification(guild_id, str(e))

                except IndexError:
                    await ctx.send("The channel you mentioned is invalid.")

                except discord.Forbidden:
                    await ctx.send("I do not have permissions to edit the message.")

        else:
            await ctx.send("You do not have an admin role.")

    @commands.command(name="reaction")
    async def edit_reaction(self, ctx):
        """adds or removes a reaction from an existing reaction role message."""
        if self.isadmin(ctx.message.author, ctx.guild.id):
            msg_values = ctx.message.content.split()
            mentioned_roles = ctx.message.role_mentions
            mentioned_channels = ctx.message.channel_mentions
            if len(msg_values) < 4:
                if not mentioned_channels:
                    await ctx.send(
                        f" To get started, type:\n```\n{self.prefix}reaction add"
                        f" #channelname\n```or\n```\n{self.prefix}reaction remove"
                        " #channelname\n```"
                    )
                    return

                channel = ctx.message.channel_mentions[0]
                all_messages = await self.formatted_channel_list(channel)
                if len(all_messages) == 1:
                    await ctx.send(
                        "There is only one reaction-role messages in this channel."
                        f" **Type**:\n```\n{self.prefix}reaction add #{channel.name} 1"
                        f" :reaction: @rolename\n```or\n```\n{self.prefix}reaction remove"
                        f" #{channel.name} 1 :reaction:\n```"
                    )
                    return

                elif len(all_messages) > 1:
                    await ctx.send(
                        f"There are **{len(all_messages)}** reaction-role messages in this"
                        f" channel. **Type**:\n```\n{self.prefix}reaction add #{channel.name}"
                        " MESSAGE_NUMBER :reaction:"
                        f" @rolename\n```or\n```\n{self.prefix}reaction remove"
                        f" #{channel.name} MESSAGE_NUMBER :reaction:\n```\nThe list of the"
                        " current reaction-role messages is:\n\n"
                        + "\n".join(all_messages)
                    )
                    return

                else:
                    await ctx.send(
                        "There are no reaction-role messages in that channel."
                    )
                    return

            action = msg_values[1].lower()
            channel = ctx.message.channel_mentions[0]
            message_number = msg_values[3]
            reaction = msg_values[4]
            if action == "add":
                if mentioned_roles:
                    role = mentioned_roles[0]
                else:
                    await ctx.send(
                        "You need to mention a role to attach to the reaction."
                    )
                    return

            all_messages = self.db.fetch_messages(channel.id)
            if isinstance(all_messages, Exception):
                await self.system_notification(
                    ctx.message.guild.id,
                    f"Database error when fetching messages:\n```\n{all_messages}\n```",
                )
                return

            counter = 1
            if all_messages:
                message_to_edit_id = None
                for msg_id in all_messages:
                    # Loop through all msg_ids and stops when the counter matches the user input
                    if str(counter) == message_number:
                        message_to_edit_id = msg_id
                        break

                    counter += 1

            else:
                await ctx.send(
                    "You selected a reaction-role message that does not exist."
                )
                return

            if message_to_edit_id:
                message_to_edit = await channel.fetch_message(int(message_to_edit_id))

            else:
                await ctx.send(
                    "Select a valid reaction-role message number (i.e. the number"
                    " to the left of the reaction-role message content in the list"
                    " above)."
                )
                return

            if action == "add":
                try:
                    # Check that the bot can actually use the emoji
                    await message_to_edit.add_reaction(reaction)

                except discord.HTTPException:
                    await ctx.send(
                        "You can only use reactions uploaded to servers the bot has access"
                        " to or standard emojis."
                    )
                    return

                react = self.db.add_reaction(
                    message_to_edit.id, role.id, reaction)
                if isinstance(react, Exception):
                    await self.system_notification(
                        ctx.message.guild.id,
                        "Database error when adding a reaction to a message in"
                        f" {message_to_edit.channel.mention}:\n```\n{react}\n```",
                    )
                    return

                if not react:
                    await ctx.send(
                        "That message already has a reaction-role combination with"
                        " that reaction."
                    )
                    return

                await ctx.send("Reaction added.")

            elif action == "remove":
                try:
                    await message_to_edit.clear_reaction(reaction)

                except discord.HTTPException:
                    await ctx.send("Invalid reaction.")
                    return

                react = self.db.remove_reaction(message_to_edit.id, reaction)
                if isinstance(react, Exception):
                    await self.system_notification(
                        ctx.message.guild.id,
                        "Database error when adding a reaction to a message in"
                        f" {message_to_edit.channel.mention}:\n```\n{react}\n```",
                    )
                    return

                await ctx.send("Reaction removed.")

        else:
            await ctx.send("You do not have an admin role.")

    @commands.command(name="systemchannel")
    async def set_systemchannel(self, ctx):
        """updates the main or server system channel where the bot sends errors and update notifications."""
        if self.isadmin(ctx.message.author, ctx.guild.id):
            msg = ctx.message.content.split()
            mentioned_channels = ctx.message.channel_mentions
            channel_type = None if len(msg) < 2 else msg[1].lower()
            if (
                len(msg) < 3
                or not mentioned_channels
                or channel_type not in ["main", "server"]
            ):
                server_channel = self.db.fetch_systemchannel(ctx.guild.id)
                if isinstance(server_channel, Exception):
                    await self.system_notification(
                        None,
                        "Database error when fetching guild system"
                        f" channels:\n```\n{server_channel}\n```",
                    )
                    return

                if server_channel:
                    server_channel = server_channel[0][0]

                # main_text = (await ctx.guild.system_channel).mention if ctx.guild.system_channel else 'none'
                server_text = (
                    (await self.getchannel(server_channel)).mention
                    if server_channel
                    else "none"
                )
                await ctx.send(
                    "Define if you are setting up a server or main system channel and"
                    f" mention the target channel.\n```\n{self.prefix}systemchannel"
                    " <main/server> #channelname\n```\nThe server system channel"
                    " reports errors and notifications related to this server only,"
                    " while the main system channel is used as a fall-back and for"
                    " bot-wide errors and notifications.\n\nThe current channels are:\n"
                    # f"**Main:** {main_text}\n"
                    f"**Server:** {server_text}"
                )
                return

            target_channel = mentioned_channels[0].id
            guild_id = ctx.message.guild.id

            server = await self.getguild(guild_id)
            bot_user = server.get_member(self.bot.user.id)
            bot_permissions = (await self.getchannel(target_channel)).permissions_for(
                bot_user
            )
            writable = bot_permissions.read_messages
            readable = bot_permissions.view_channel
            if not writable or not readable:
                await ctx.send("I cannot read or send messages in that channel.")
                return

            if channel_type == "server":
                add_channel = self.db.add_systemchannel(
                    guild_id, target_channel)

                if isinstance(add_channel, Exception):
                    await self.system_notification(
                        guild_id,
                        "Database error when adding a new system"
                        f" channel:\n```\n{add_channel}\n```",
                    )
                    return

            await ctx.send("System channel updated.")

        else:
            await ctx.send("You do not have an admin role.")

    @commands.command(name="notify")
    async def toggle_notify(self, ctx):
        """toggles sending messages to users when they get/lose a role (default off) for the current server (the command affects only the server it was used in)."""
        if self.isadmin(ctx.message.author, ctx.guild.id):
            notify = self.db.toggle_notify(ctx.guild.id)
            if notify:
                await ctx.send(
                    "Notifications have been set to **ON** for this server.\n"
                    "Use this command again to turn them off."
                )
            else:
                await ctx.send(
                    "Notifications have been set to **OFF** for this server.\n"
                    "Use this command again to turn them on."
                )

    @commands.command(pass_context=True, name="admin")
    @commands.has_permissions(administrator=True)
    async def add_admin(self, ctx, role: discord.Role):
        """adds the mentioned role or role id to the admin list, allowing members with a certain role to use the bot commands. Requires administrator permissions on the server."""
        # Adds an admin role ID to the database
        add = self.db.add_admin(role.id, ctx.guild.id)

        if isinstance(add, Exception):
            await self.system_notification(
                ctx.message.guild.id,
                f"Database error when adding a new admin:\n```\n{add}\n```",
            )
            return

        await ctx.send("Added the role to my admin list.")

    @add_admin.error
    async def add_admin_error(self, ctx, error):
        if isinstance(error, commands.RoleNotFound):
            await ctx.send("Please mention a valid @Role or role ID.")

    @commands.command(name="rm-admin")
    @commands.has_permissions(administrator=True)
    async def remove_admin(self, ctx, role: discord.Role):
        """removes the mentioned role or role id from the admin list, preventing members with a certain role from using the bot commands. Requires administrator permissions on the server."""
        # Removes an admin role ID from the database
        remove = self.db.remove_admin(role.id, ctx.guild.id)

        if isinstance(remove, Exception):
            await self.system_notification(
                ctx.message.guild.id,
                f"Database error when removing an admin:\n```\n{remove}\n```",
            )
            return

        await ctx.send("Removed the role from my admin list.")

    @commands.command(name="adminlist")
    @commands.has_permissions(administrator=True)
    async def list_admin(self, ctx):
        """lists the current admins on the server the command was run in by mentioning them and the current admins from other servers by printing out the role IDs. Requires administrator permissions on the server."""
        # Lists all admin IDs in the database, mentioning them if possible
        admin_ids = self.db.get_admins(ctx.guild.id)

        if isinstance(admin_ids, Exception):
            await self.system_notification(
                ctx.message.guild.id,
                f"Database error when fetching admins:\n```\n{admin_ids}\n```",
            )
            return

        adminrole_objects = []
        for admin_id in admin_ids:
            adminrole_objects.append(
                discord.utils.get(ctx.guild.roles, id=admin_id).mention
            )

        if adminrole_objects:
            await ctx.send(
                "The bot admins on this server are:\n- "
                + "\n- ".join(adminrole_objects)
            )
        else:
            await ctx.send("There are no bot admins registered in this server.")

    @remove_admin.error
    async def remove_admin_error(self, ctx, error):
        if isinstance(error, commands.RoleNotFound):
            await ctx.send("Please mention a valid @Role or role ID.")


def setup(bot):
    bot.add_cog(ReactionRoles(bot))
