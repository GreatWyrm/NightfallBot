import discord.ext.commands
import discord.ext.tasks
from discord import Interaction, Attachment, DMChannel
from discord.ext import commands
from discord.ext.commands import Cog, has_permissions
from discord.ext.commands import Context
from discord.ui import Label, TextInput, FileUpload

import configreader
import nightfall_discord

notifiedUsers = list()

unban_message_submitters = list()

# What threads allow messages to be sent from them to the user they are about.
open_threads = list()

thank_you_form_text = ("Thank you for your submission!\n"
                       "Our staff team will review it and contact you through this bot if needed.")

# approvedTag = discord.ForumTag()

# deniedTag = discord.ForumTag()

handledTag = discord.ForumTag(name="Handled")


def has_user_sent_unban_request(user: discord.User | discord.Member) -> bool:
    if unban_message_submitters.__contains__(user):
        return True
    else:
        return False


class DirectMessageHandler(Cog):
    @commands.Cog.listener()
    async def on_ready(self):
        nightfall_discord.nf_bot.add_view(view=BugPublicReportView())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author != nightfall_discord.nf_bot.user and isinstance(message.channel, discord.DMChannel) and not notifiedUsers.__contains__(
            message.author):
            channel = message.channel
            await channel.send("Hello! Here are the current available actions you may perform, if there is a problem, try re-messaging me.",
                               view=MenuView())
            notifiedUsers.append(message.author)

    @commands.Command
    @has_permissions(manage_messages=True)
    async def bug_report(self, ctx: commands.Context):
        await ctx.channel.send(content='Hit the button to submit a bug report.',
                           view=BugPublicReportView(), silent=True)


class BugPublicReportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Report Bug", style=discord.ButtonStyle.green, emoji="🐛", custom_id="bug_button"))
        self.children[-1].callback = self.callback


    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(BugReportModal(False))


class MenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Issue", style=discord.ButtonStyle.primary, emoji="📝", custom_id="issue_button")
    async def button_callback_open_issue(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.send_modal(IssueModal())

    @discord.ui.button(label="Report Bug", style=discord.ButtonStyle.green, emoji="🐛", custom_id="bug_button")
    async def button_callback_report_bug(self, interaction, button: discord.Button):
        await interaction.response.send_modal(BugReportModal(False))

    @discord.ui.button(label="Request Unban", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="unban_button")
    async def button_callback_opt2(self, interaction: discord.Interaction, button: discord.Button):
        if has_user_sent_unban_request(interaction.user):
            await interaction.response.send_message(
                "You have already sent a ban request, please wait for a response before sending another one!")
        else:
            await interaction.response.send_modal(UnbanModal())


class ThreadModal(discord.ui.Modal):
    def __init__(self, custom_id: str):
        super().__init__(custom_id=custom_id, timeout=None)

    async def create_thread(self, interaction: Interaction, channel_id: int, name: str, reason: str, color: discord.Colour, attachments: list[Attachment] | None = None):
        if attachments is None:
            attachments = list()
        attached_files = list()
        for attachment in attachments:
            attached_files.append(await attachment.to_file())
        channel = nightfall_discord.nf_bot.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.ForumChannel):
            if isinstance(channel, discord.ForumChannel):
                embed = discord.Embed(description=self.create_message(interaction),
                                      color=color)
                embed.set_thumbnail(url=interaction.user.avatar.url)
                newThread = await channel.create_thread(name=name,
                                            embed=embed, reason=reason)
                if attached_files.__len__() > 0:
                    await newThread.thread.send(content="User attached files.", files=attached_files)
            elif isinstance(channel, discord.TextChannel):
                thread = await channel.create_thread(name=name,
                                                     invitable=False, reason=reason)
                embed = discord.Embed(description=self.create_message(interaction),
                                      color=color)
                embed.set_thumbnail(url=interaction.user.avatar.url)
                await thread.send(embed=embed)
                if attached_files.__len__() > 0:
                 await thread.send(content="User attached files.", files=attached_files)
                await channel.send(thread.jump_url)
            else:
                print("Tried to create a thread in a non text or forum channel!")
        else:
            print(f"Failed to find a text or forum channel for channel {channel} and channel ID {channel.id}")

    def create_message(self, interaction) -> str:
        return ""


class IssueModal(ThreadModal, title="Issue Form"):
    username_input = TextInput(label = "Minecraft Username",
                                          placeholder="Your Username",
                                          required=False,
                                          min_length=2,
                                          max_length=16,
                                          id=100,
                                          custom_id="issue_user_input")
    issue_name_input = TextInput(label="What is the issue?",
                                            placeholder="...",
                                            style=discord.TextStyle.short,
                                            max_length=50,
                                            required=True,
                                            id=101,
                                            custom_id="issue_name_input")
    issue_description_input = TextInput(label="Describe the issue in more depth here.",
                                                   placeholder="...",
                                                   style=discord.TextStyle.paragraph,
                                                   max_length=1000,
                                                   required=False,
                                                   id=102,
                                                   custom_id="issue_description_input")
    issue_attached_label = Label(text="Attach any related files here.",
                                 component=FileUpload(required=False,
                                                      min_values=0,
                                                      max_values=10,
                                                      id=104,
                                                      custom_id="issue_attachment_input"),
                                 id=103)

    def __init__(self):
        super().__init__(custom_id="issue_thread_model")
        self.channel = configreader.bot_issue_channel_id
        self.reason = configreader.bot_issue_internal_reason

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(content=thank_you_form_text, ephemeral=True, silent=True)

        await self.create_thread(interaction, self.channel, self.issue_name_input.value, self.reason, discord.Colour.blue(), self.issue_attached_label.component.values)

    # example_user : 34283492934
    #
    # MC Username: Notch
    #
    # Description of the bug:
    # Bug no worky.
    def create_message(self, interaction) -> str:
        username = ""
        issue_description = ""
        if self.username_input.value:
            username = f"\n\n### MC Username:\n{self.username_input.value}"
        if self.issue_description_input.value:
            issue_description = f'\n\n### In-depth explanation of the issue:\n{self.issue_description_input.value}'
        return (f"{interaction.user.name} : {interaction.user.id} {username} {issue_description}"
                )


class BugReportModal(ThreadModal, title="Bug Report Form"):
    username_input = TextInput(label="Minecraft Username",
                               placeholder="Your Username",
                               required=False,
                               min_length=2,
                               max_length=16,
                               id=200,
                               custom_id="bug_user_input")
    bug_name_input = TextInput(label="What is the bug you are reporting?",
                               placeholder="...",
                               style=discord.TextStyle.short,
                               max_length=50,
                               required=True,
                               id=201,
                               custom_id="bug_input")
    bug_description_input = TextInput(label="Describe the bug here.",
                                      placeholder="...",
                                      style=discord.TextStyle.paragraph,
                                      max_length=1000,
                                      required=True,
                                      id=202,
                                      custom_id="bug_description_input")
    issue_attached_label = Label(text="Attach any related files here.",
                                 component=FileUpload(required=False,
                                                      min_values=0,
                                                      max_values=10,
                                                      id=204,
                                                      custom_id="bug_attached_input"),
                                 id=203)

    def __init__(self, delete_message: bool):
        super().__init__(custom_id="bug_thread_model")
        self.delete_message = delete_message

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(content=thank_you_form_text, ephemeral=True, silent=True)
        if self.delete_message:
            await interaction.message.delete()
            user = interaction.user
            notifiedUsers.remove(user)

        await self.create_thread(interaction, configreader.bot_bug_channel_id, self.bug_name_input.value, configreader.bot_bug_internal_reason, discord.Colour.green(), self.issue_attached_label.component.values)

    # example_user : 34283492934
    #
    # MC Username: Notch
    #
    # Description of the bug:
    # Bug no worky.
    def create_message(self, interaction) -> str:
        username = ""
        bug_description = ""

        if self.username_input.value:
            username = f"\n\n### MC Username:\n{self.username_input.value}"

        if self.bug_description_input:
            bug_description = f"\n\n### Description of the bug:\n{self.bug_description_input.value}"

        return f"{interaction.user.name} : {interaction.user.id} {username} {bug_description}"


class UnbanModal(ThreadModal, title="Unban Request Form"):
    username_input = TextInput(label = "Minecraft Username",
                               placeholder="Your Username",
                               min_length=2,
                               max_length=16,
                               required=True,
                               id=300,
                               custom_id="unban_user_input")
    ban_reason_input = TextInput(label="Why were you banned?",
                                 placeholder="Place your ban message here.",
                                 style=discord.TextStyle.short,
                                 max_length=100,
                                 required=True,
                                 id=301,
                                 custom_id="unban_when_input")
    unban_should_input = TextInput(label="Why should you be unbanned?",
                                   placeholder="...",
                                   style=discord.TextStyle.paragraph,
                                   max_length=1000,
                                   required=True,
                                   id=302,
                                   custom_id="unban_what_input")
    unban_want_input = TextInput(label="Why do you want to be unbanned?",
                                 placeholder="...",
                                 style=discord.TextStyle.paragraph,
                                 max_length=1000,
                                 required=True,
                                 id=303,
                                 custom_id="unban_why_input")

    def __init__(self):
        super().__init__(custom_id="unban_thread_model")
        self.channel = configreader.bot_unban_channel_id
        self.reason = configreader.bot_unban_internal_reason

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(thank_you_form_text, ephemeral=True)
        user = interaction.user

        await self.create_thread(interaction=interaction,
                                 channel_id=self.channel,
                                 name=f"{user.name} : {user.id}",
                                 reason=self.reason,
                                 color=discord.Colour.red())
        unban_message_submitters.append(interaction.user)

    # Minecraft Username: ___________
    #
    # Why should I be unbanned? __________
    #
    # Why would I want to be unbanned? ____________
    #
    # Why was I banned? __________
    def create_message(self, interaction) -> str:
        unban_should = ""
        unban_want = ""
        ban_reason = ""

        if self.unban_should_input:
            unban_should = f"\n\n### Why should I be unbanned?\n{self.unban_should_input.value}"
        if self.unban_want_input:
            unban_want = f"\n\n### Why would I want to be unbanned?\n{self.unban_want_input.value}"
        if self.ban_reason_input:
            ban_reason = f"\n\n### Why was I banned?\n{self.ban_reason_input.value}"

        return f"## MC Username: {self.username_input.value} {unban_want} {unban_should} {ban_reason}"


def get_user_from_thread(words: str | None):
    if words:
        first_step = str(words.partition(":")[2])
        if first_step == "":
            return None
        second_step = first_step.partition("\n")[0]
        if second_step == "":
            return None
        return nightfall_discord.nf_bot.get_user(int(second_step))
    else:
        return None


def get_user_from_ban_thread(name: str | None) -> discord.User | None:
    if name:
        user_id = int(name.partition(":")[2])
        return nightfall_discord.nf_bot.get_user(user_id)
    else:
        return None


class ThreadHandler(Cog):

    @commands.Cog.listener()
    async def on_ready(self):
        guild = nightfall_discord.nf_bot.get_guild(configreader.bot_reports_guild_id)
        if guild:
            channel = nightfall_discord.nf_bot.get_channel(configreader.bot_unban_channel_id)
            if channel:
                for thread in channel.threads:
                    user = get_user_from_ban_thread(thread.name)
                    if user:
                        unban_message_submitters.append(user)
            else:
                print("Bot Unban Channel not found!")
        else:
            print("Bot Report Guild not found!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content.startswith("!"):
            return
        if message.author == nightfall_discord.nf_bot.user or not message.guild or (
                message.guild and message.guild.id != configreader.bot_reports_guild_id) or not message.channel:
            return

        thread = message.guild.get_thread(message.channel.id)

        if thread and open_threads.__contains__(thread):
            parent_id = thread.parent_id
            if configreader.bot_reports_guild_id == parent_id:
                await self.on_unban_thread_message(message)
            elif configreader.bot_bug_channel_id == parent_id:
                await self.on_thread_message(message, discord.Colour.green())
            elif configreader.bot_issue_channel_id == parent_id:
                await self.on_thread_message(message, discord.Colour.blue())

    async def cog_check(self, ctx: Context) -> bool:
        if ctx.guild.id != configreader.bot_reports_guild_id:
            print(f"User: {ctx.author} Id: {ctx.author.id} tried to send a message or use a command in an invalid guild!")
            raise discord.ext.commands.GuildNotFound("")
        if not ctx.channel:
            raise discord.ext.commands.ChannelNotFound("")
        if not isinstance(ctx.channel, discord.Thread):
            raise discord.ext.commands.ThreadNotFound("")
        channel_id = ctx.channel.parent.id
        if not configreader.bot_valid_thread_ids.__contains__(channel_id):
            raise discord.ext.commands.BadArgument()
        return True

    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, discord.ext.commands.GuildNotFound):
            await ctx.send("You cannot use this in an invalid guild.", ephemeral=True)
            return
        if isinstance(error, discord.ext.commands.ChannelNotFound):
            await ctx.send("You cannot use this in an invalid channel.", ephemeral=True)
            return
        if isinstance(error, discord.ext.commands.ThreadNotFound):
            await ctx.send("You cannot use this in an channel is not a thread.", ephemeral=True)
            return
        if isinstance(error, discord.ext.commands.BadArgument):
            await ctx.send("You cannot use this in an invalid thread.", ephemeral=True)
            return

    @commands.command(name="open_thread")
    @commands.has_role("Admin")
    async def open_thread(self, ctx: discord.ext.commands.Context):
        if open_threads.__contains__(ctx.channel):
            await ctx.send("Cannot close channel, channel is already closed.")
        else:
            open_threads.append(ctx.channel)
            await ctx.send("Opened channel, all messages will now be relayed to the ticket owner.")

    @commands.command(name="close_thread")
    @commands.has_role("Admin")
    async def close_thread(self, ctx: discord.ext.commands.Context):
        if not open_threads.__contains__(ctx.channel):
            await ctx.send("Cannot close channel, channel is already closed.")
        else:
            open_threads.remove(ctx.channel)
            await ctx.send("Closed channel, messages sent will not be relayed to the ticket maker.")

    async def cog_unload(self) -> None:
        for thread in open_threads:
            if thread.guild.get_thread(thread.id):
                await thread.send("This thread is now closed, messages sent will not be relayed to the ticket maker.")
        open_threads.clear()
        return

    async def on_thread_message(self, message: discord.Message, color):
        if not message.author.bot:
            starter_message = [message async for message in message.channel.history(oldest_first=True, limit=1)][0]
            user = get_user_from_thread(starter_message.embeds[0].description)
            if user:
                dm_channel: DMChannel | None = user.dm_channel
                if not dm_channel:
                    print("DMChannel for user was missing. Creating a new one.")
                    dm_channel: DMChannel = await user.create_dm()

                embed = discord.Embed(description=f"Staff: {message.content}",
                                      color=color)
                embed.set_author(name=message.channel.name)
                await dm_channel.send(embed=embed, view=ButtonResponseView(message.channel, message.channel.name, color))
            else:
                print(f"Tried to message a user that did not exist? Channel: {message.channel.name} Id: {message.channel.id}")

    async def on_unban_thread_message(self, message):
        if not message.author.bot:
            user = get_user_from_ban_thread(message.channel.name)
            if user:
                dm_channel: DMChannel | None = user.dm_channel
                if not dm_channel:
                    print("DMChannel for user was missing. Creating a new one.")
                    dm_channel: DMChannel = await user.create_dm()
                embed = discord.Embed(description=f"Moderator: {message.content}",
                                      color=discord.Colour.red())
                embed.set_author(name="Unban Request Chat")
                await dm_channel.send(embed=embed, view=ButtonResponseView(message.channel, "Unban Request Chat", discord.Colour.red()))
            else:
                print(f"Tried to message a user that did not exist? Channel: {message.channel.name} Id: {message.channel.id}")


class ButtonResponseView(discord.ui.View):
    def __init__(self, channel, name, color):
        super().__init__()
        self.channel = channel
        self.name = name
        self.color = color

    @discord.ui.button(label="Respond", style=discord.ButtonStyle.danger, emoji="📝")
    async def response_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.channel:
            await interaction.response.send_modal(ResponseModal(self.channel, self.name, self.color))
        else:
            await interaction.response.send_message("This chat has concluded.")


class ResponseModal(discord.ui.Modal, title="Text Response"):
    response = discord.ui.TextInput(label="Your Response",
                                    max_length=300)

    def __init__(self, channel, name, color):
        super().__init__()
        self.channel = channel
        self.name = name
        self.color = color

    async def on_submit(self, interaction: Interaction) -> None:
        user_embed = discord.Embed(description=f"You: {self.response.value}",
                                  color=self.color)
        user_embed.set_author(name=self.name)
        await interaction.message.reply(embed=user_embed)

        if self.channel:
            admin_embed = discord.Embed(description=self.response.value,
                                       color=self.color)
            admin_embed.set_author(name=interaction.user.name)
            await self.channel.send(embed=admin_embed)
