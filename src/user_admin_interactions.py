import discord.ext.commands
import discord.ext.tasks
from discord import Interaction
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext.commands import Cog

from configreader import ConfigReader

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
    def __init__(self, bot: Bot, config: ConfigReader):
        self.bot = bot
        self.config = config

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author != self.bot.user and isinstance(message.channel,
                                                          discord.DMChannel) and not notifiedUsers.__contains__(
            message.author):
            channel = message.channel
            await channel.send("Hello! Here are the current available actions you may perform:",
                               view=MenuView(self.bot, self.config))
            notifiedUsers.append(message.author)


class MenuView(discord.ui.View):

    def __init__(self, bot: Bot, config: ConfigReader):
        super().__init__()
        self.bot = bot
        self.config = config

    @discord.ui.button(label="Open Issue", style=discord.ButtonStyle.primary, emoji="📝")
    async def button_callback_open_issue(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.send_message("Not implemented yet.")

    @discord.ui.button(label="Report Bug", style=discord.ButtonStyle.green, emoji="🐛")
    async def button_callback_report_bug(self, interaction, button: discord.Button):
        await interaction.response.send_message("Not implemented yet.")

    @discord.ui.button(label="Request Unban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def button_callback_opt2(self, interaction: discord.Interaction, button: discord.Button):
        if has_user_sent_unban_request(interaction.user):
            await interaction.response.send_message(
                "You have already sent a ban request, please wait for a response before sending another one!")
        else:
            await interaction.response.send_modal(UnbanModal(self.bot, self.config))


class ThreadModal(discord.ui.Modal):

    def __init__(self, bot: Bot, config: ConfigReader):
        super().__init__()
        self.bot = bot
        self.config = config

    async def create_thread(self, interaction: Interaction, channel_id: int, name: str, reason: str):
        channel = self.bot.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel) or isinstance(channel, discord.ForumChannel):
            if isinstance(channel, discord.ForumChannel):
                embed = discord.Embed(description=self.create_message(),
                                      color=discord.Colour.red())
                embed.set_thumbnail(url=interaction.user.avatar.url)
                await channel.create_thread(name=name,
                                            embed=embed, reason=reason)
            else:
                if isinstance(channel, discord.TextChannel):
                    thread = await channel.create_thread(name=name,
                                                         invitable=False, reason=reason)
                    embed = discord.Embed(description=self.create_message(),
                                          color=discord.Colour.red())
                    embed.set_thumbnail(url=interaction.user.avatar.url)
                    await thread.send(embed=embed)
                    await channel.send(thread.jump_url)
                else:
                    print("Tried to create a thread in a non text or forum channel!")
        else:
            print(f"Failed to find a text or forum channel for channel {channel} and channel ID {channel.id}")

    def create_message(self) -> str:
        return ""


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

    def __init__(self, bot: Bot, config: ConfigReader):
        super().__init__(bot, config)
        self.channel = config.bot_unban_channel_id
        self.reason = config.bot_unban_internal_reason

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(thank_you_form_text)
        await interaction.message.delete()
        user = interaction.user
        notifiedUsers.remove(user)

        await self.create_thread(interaction, self.channel, f"{user.name} : {user.id}", self.reason)
        unban_message_submitters.append(interaction.user)

    # Minecraft Username: ___________
    #
    # Why should I be unbanned? __________
    #
    # Why would I want to be unbanned? ____________
    #
    # Why was I banned? __________
    def create_message(self) -> str:
        return (f"### MC Username: {self.username_prompt.value}\n\n"
                f"Why should I be unbanned?\n{self.unban_should_prompt.value}\n\n"
                f"Why would I want to be unbanned?\n{self.unban_want_prompt.value}\n\n"
                f"Why was I banned?\n{self.ban_reason_prompt.value}"
                )


class ThreadHandler(Cog):
    def __init__(self, bot: Bot, config: ConfigReader):
        self.bot = bot
        self.config = config

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(self.config.bot_reports_guild_id)
        if guild:
            channel = self.bot.get_channel(self.config.bot_unban_channel_id)
            if channel:
                for thread in channel.threads:
                    user = self.get_user_from_thread_name(thread.name)
                    if user:
                        unban_message_submitters.append(user)
            else:
                print("Bot Unban Channel not found!")
        else:
            print("Bot Report Guild not found!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user or not message.guild or (
                message.guild and message.guild.id != self.config.bot_reports_guild_id) or not message.channel:
            return

        thread = message.guild.get_thread(message.channel.id)

        if thread and thread.parent and thread.parent_id == self.config.bot_unban_channel_id:
            await self.on_unban_thread_message(message)

    async def cog_unload(self) -> None:
        for thread in open_threads:
            thread.send("This thread is now closed, messages sent will not be sent to the ticket maker.")
        return

    # Add a condition to make sure the thread is open to send messages later.
    async def on_unban_thread_message(self, message):
        if not message.author.bot:
            user = self.get_user_from_thread_name(message.channel.name)
            if user:
                embed = discord.Embed(description=f"Moderator: {message.content}",
                                      color=discord.Colour.red())
                embed.set_author(name="Unban Request Chat")
                await user.send(embed=embed, view=ButtonResponseView(message.channel))
            else:
                print("Tried to message a user that did not exist?")

    def get_user_from_thread_name(self, str) -> discord.User:
        user_id = int(str.partition(":")[2])
        return self.bot.get_user(user_id)


class ButtonResponseView(discord.ui.View):

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    @discord.ui.button(label="Respond", style=discord.ButtonStyle.danger, emoji="📝")
    async def response_callback(self, interaction: discord.Interaction, button: discord.Button):
        if self.channel:
            await interaction.response.send_modal(ResponseModal(self.channel))
        else:
            await interaction.response.send_message("This chat has concluded.")


class ResponseModal(discord.ui.Modal, title="Text Response"):
    response = discord.ui.TextInput(label="Your Response",
                                    max_length=300)

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: Interaction) -> None:
        userEmbed = discord.Embed(description=f"You: {self.response.value}",
                                  color=discord.Colour.red())
        userEmbed.set_author(name="Unban Request Chat")
        await interaction.message.reply(embed=userEmbed)

        if self.channel:
            adminEmbed = discord.Embed(description=self.response.value,
                                       color=discord.Colour.red())
            adminEmbed.set_author(name=interaction.user.name)
            await self.channel.send(embed=adminEmbed)
