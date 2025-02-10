import discord.ext.commands
import discord.ext.tasks
from discord import Interaction
from discord.ext import commands, tasks
from discord.ext.commands import Cog
from discord.ext.commands import Context

import configreader
import nightfall_discord

notifiedUsers = list()

unban_message_submitters = list()

# What threads allow messages to be sent from them to the user they are about.
open_threads = list()

thank_you_form_text = ("Thank you for submitting the form!\n"
                       "Our staff team will review it and contact you through this bot if needed.")

# approvedTag = discord.ForumTag()

# deniedTag = discord.ForumTag()

handledTag = discord.ForumTag(name="Handled")


def has_user_sent_unban_request(user: discord.User) -> bool:
    if unban_message_submitters.__contains__(user):
        return True
    else:
        return False


class DirectMessageHandler(Cog):
    bug_message = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.sendBugReportMessage(configreader.bot_bug_report_button_channel_id)
        self.refreshBugButton.change_interval(minutes=5)
        self.refreshBugButton.start()

    async def cog_unload(self) -> None:
        await self.removeBugReportMessage()
        self.refreshBugButton.stop()

    @tasks.loop()
    async def refreshBugButton(self):
        if self.bug_message:
            self.bug_message = await self.bug_message.edit(content='Hit the button to submit a bug report.',
                                                           view=BugPublicReportView())

    async def sendBugReportMessage(self, channel_id):
        if channel_id:
            id = int(channel_id)
            channel = nightfall_discord.nf_bot.get_channel(id)
            if channel:
                self.bug_message = await channel.send(content='Hit the button to submit a bug report.',
                                                      view=BugPublicReportView(), silent=True)

    async def removeBugReportMessage(self):
        if self.bug_message is not None:
            await self.bug_message.delete()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author != nightfall_discord.nf_bot.user and message.channel.id == configreader.bot_bug_report_button_channel_id and not message.author.guild_permissions.administrator:
            await message.delete()

        if message.author != nightfall_discord.nf_bot.user and isinstance(message.channel,
                                                          discord.DMChannel) and not notifiedUsers.__contains__(
            message.author):
            channel = message.channel
            await channel.send("Hello! Here are the current available actions you may perform:",
                               view=MenuView())
            notifiedUsers.append(message.author)


class BugPublicReportView(discord.ui.View):
    @discord.ui.button(label="Report Bug", style=discord.ButtonStyle.green, emoji="🐛")
    async def button_callback_report_bug(self, interaction, button: discord.Button):
        await interaction.response.send_modal(BugReportModal(False))


class MenuView(discord.ui.View):
    @discord.ui.button(label="Open Issue", style=discord.ButtonStyle.primary, emoji="📝")
    async def button_callback_open_issue(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.send_modal(IssueModal(self.bot, self.config))

    @discord.ui.button(label="Report Bug", style=discord.ButtonStyle.green, emoji="🐛")
    async def button_callback_report_bug(self, interaction, button: discord.Button):
        await interaction.response.send_modal(BugReportModal(self.bot, self.config, True))

    @discord.ui.button(label="Request Unban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def button_callback_opt2(self, interaction: discord.Interaction, button: discord.Button):
        if has_user_sent_unban_request(interaction.user):
            await interaction.response.send_message(
                "You have already sent a ban request, please wait for a response before sending another one!")
        else:
            await interaction.response.send_modal(UnbanModal())


class ThreadModal(discord.ui.Modal):
    async def create_thread(self, interaction: Interaction, channel_id: int, name: str, reason: str,
                            color: discord.Colour):
        channel = nightfall_discord.nf_bot.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.ForumChannel):
            if isinstance(channel, discord.ForumChannel):
                embed = discord.Embed(description=self.create_message(interaction),
                                      color=color)
                embed.set_thumbnail(url=interaction.user.avatar.url)
                await channel.create_thread(name=name,
                                            embed=embed, reason=reason)
            elif isinstance(channel, discord.TextChannel):
                thread = await channel.create_thread(name=name,
                                                     invitable=False, reason=reason)
                embed = discord.Embed(description=self.create_message(interaction),
                                      color=color)
                embed.set_thumbnail(url=interaction.user.avatar.url)
                await thread.send(embed=embed)
                await channel.send(thread.jump_url)
            else:
                print("Tried to create a thread in a non text or forum channel!")
        else:
            print(f"Failed to find a text or forum channel for channel {channel} and channel ID {channel.id}")

    def create_message(self, interaction) -> str:
        return ""


class IssueModal(ThreadModal, title="Issue Form"):
    username_prompt = discord.ui.TextInput(label="Minecraft Username(Optional)",
                                           placeholder="Your Username",
                                           row=0,
                                           required=False,
                                           min_length=2,
                                           max_length=16)
    issue_name = discord.ui.TextInput(label="What is the issue?",
                                      placeholder="...",
                                      style=discord.TextStyle.short,
                                      max_length=50,
                                      required=True, row=1)
    issue_description = discord.ui.TextInput(label="Describe the issue in more depth here.",
                                             placeholder="...",
                                             style=discord.TextStyle.paragraph,
                                             max_length=1000,
                                             required=False, row=2)

    def __init__(self):
        super().__init__()
        self.channel = configreader.bot_issue_channel_id
        self.reason = configreader.bot_issue_internal_reason

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(content=thank_you_form_text, ephemeral=True, silent=True)
        await interaction.message.delete()
        user = interaction.user
        notifiedUsers.remove(user)

        await self.create_thread(interaction, self.channel, self.issue_name.value, self.reason, discord.Colour.blue())

    # example_user : 34283492934
    #
    # MC Username: Notch
    #
    # Description of the bug:
    # Bug no worky.
    def create_message(self, interaction) -> str:
        username = ""
        issue_description = ""
        if self.username_prompt.value:
            username = f"\n\n### MC Username:\n{self.username_prompt.value}"
        if self.issue_description.value:
            issue_description = f'\n\n### In-depth explanation of the issue:\n{self.issue_description.value}'
        return (f"{interaction.user.name} : {interaction.user.id} {username} {issue_description}"
                )


class BugReportModal(ThreadModal, title="Bug Report Form"):
    username_prompt = discord.ui.TextInput(label="Minecraft Username(Optional)",
                                           placeholder="Your Username",
                                           row=0,
                                           required=False,
                                           min_length=2,
                                           max_length=16)
    bug_name = discord.ui.TextInput(label="What is the name of the bug?",
                                    placeholder="...",
                                    style=discord.TextStyle.short,
                                    max_length=50,
                                    required=True, row=1)
    bug_description = discord.ui.TextInput(label="Describe the bug here.",
                                           placeholder="...",
                                           style=discord.TextStyle.paragraph,
                                           max_length=1000,
                                           required=False, row=2)

    def __init__(self, delete_message: bool):
        super().__init__()
        self.delete_message = delete_message

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(content=thank_you_form_text, ephemeral=True, silent=True)
        if self.delete_message:
            await interaction.message.delete()
            user = interaction.user
            notifiedUsers.remove(user)

        await self.create_thread(interaction, self.channel, self.bug_name.value, self.reason, discord.Colour.green())

    # example_user : 34283492934
    #
    # MC Username: Notch
    #
    # Description of the bug:
    # Bug no worky.
    def create_message(self, interaction) -> str:
        username = ""
        bug_description = ""

        if self.username_prompt.value:
            username = f"\n\n### MC Username:\n{self.username_prompt.value}"

        if self.bug_description:
            bug_description = f"\n\n### Description of the bug:\n{self.bug_description.value}"

        return f"{interaction.user.name} : {interaction.user.id} {username} {bug_description}"


class UnbanModal(ThreadModal, title="Unban Request Form"):
    username_prompt = discord.ui.TextInput(label="Minecraft Username",
                                           placeholder="Your Username",
                                           row=0,
                                           min_length=2,
                                           max_length=16)
    unban_should_prompt = discord.ui.TextInput(label="Why should you be unbanned?",
                                               placeholder="...",
                                               style=discord.TextStyle.paragraph,
                                               max_length=1000,
                                               required=False, row=2)
    unban_want_prompt = discord.ui.TextInput(label="Why do you want to be unbanned?",
                                             placeholder="...",
                                             style=discord.TextStyle.paragraph,
                                             max_length=1000,
                                             required=False, row=1)
    ban_reason_prompt = discord.ui.TextInput(label="Why were you banned?",
                                             placeholder="Place your ban message here.",
                                             max_length=500,
                                             style=discord.TextStyle.paragraph,
                                             required=False, row=3)

    def __init__(self):
        super().__init__()
        self.channel = configreader.bot_unban_channel_id
        self.reason = configreader.bot_unban_internal_reason

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(thank_you_form_text)
        await interaction.message.delete()
        user = interaction.user
        notifiedUsers.remove(user)

        await self.create_thread(interaction, self.channel, f"{user.name} : {user.id}", self.reason,
                                 discord.Colour.red())
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

        if self.unban_should_prompt:
            unban_should = f"\n\n### Why should I be unbanned?\n{self.unban_should_prompt.value}"
        if self.unban_want_prompt:
            unban_want = f"\n\n### Why would I want to be unbanned?\n{self.unban_want_prompt.value}"
        if self.ban_reason_prompt:
            ban_reason = f"\n\n### Why was I banned?\n{self.ban_reason_prompt.value}"

        return f"## MC Username: {self.username_prompt.value} {unban_want} {unban_should} {ban_reason}"


class ThreadHandler(Cog):

    def __init__(self):
        self.bot = nightfall_discord.nf_bot
    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(configreader.bot_reports_guild_id)
        if guild:
            channel = self.bot.get_channel(configreader.bot_unban_channel_id)
            if channel:
                for thread in channel.threads:
                    user = self.get_user_from_ban_thread(thread.name)
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
        if message.author == self.bot.user or not message.guild or (
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
            print(
                f"User: {ctx.author} Id: {ctx.author.id} tried to send a message or use a command in an invalid guild!")
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
            await ctx.send("You cannot use this in an invalid guild.")
            return
        if isinstance(error, discord.ext.commands.ChannelNotFound):
            await ctx.send("You cannot use this in an invalid channel.")
            return
        if isinstance(error, discord.ext.commands.ThreadNotFound):
            await ctx.send("You cannot use this in an channel is not a thread.")
            return
        if isinstance(error, discord.ext.commands.BadArgument):
            await ctx.send("You cannot use this in an invalid thread.")
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

    async def on_thread_message(self, message, color):
        if not message.author.bot:
            starter_message = [message async for message in message.channel.history(oldest_first=True, limit=1)][0]
            user = self.get_user_from_thread(starter_message.embeds[0].description)
            if user:
                embed = discord.Embed(description=f"Staff: {message.content}",
                                      color=color)
                embed.set_author(name=message.channel.name)
                await user.send(embed=embed, view=ButtonResponseView(message.channel, message.channel.name, color))
            else:
                print(
                    f"Tried to message a user that did not exist? Channel: {message.channel.name} Id: {message.channel.id}")

    async def on_unban_thread_message(self, message):
        if not message.author.bot:
            user = self.get_user_from_ban_thread(message.channel.name)
            if user:
                embed = discord.Embed(description=f"Moderator: {message.content}",
                                      color=discord.Colour.red())
                embed.set_author(name="Unban Request Chat")
                await user.send(embed=embed, view=ButtonResponseView(message.channel))
            else:
                print("Tried to message a user that did not exist?")

    def get_user_from_thread(self, words: str):
        first_step = str(words.partition(":")[2])
        if first_step == "":
            return None
        second_step = first_step.partition("\n")[0]
        if second_step == "":
            return None
        return self.bot.get_user(int(second_step))

    def get_user_from_ban_thread(self, str) -> discord.User:
        user_id = int(str.partition(":")[2])
        return self.bot.get_user(user_id)


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
        userEmbed = discord.Embed(description=f"You: {self.response.value}",
                                  color=self.color)
        userEmbed.set_author(name=self.name)
        await interaction.message.reply(embed=userEmbed)

        if self.channel:
            adminEmbed = discord.Embed(description=self.response.value,
                                       color=self.color)
            adminEmbed.set_author(name=interaction.user.name)
            await self.channel.send(embed=adminEmbed)
