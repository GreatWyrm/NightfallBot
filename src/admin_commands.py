
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Context

import configreader


async def show_message_attachment(ctx : Context, channel_id : int, attachments : list[discord.Attachment]):
    channel = ctx.guild.get_channel(channel_id)
    if channel:
        for attachment in attachments:
            if not attachment.is_voice_message():
                await channel.send((await attachment.read()).decode('utf-8'))
    else:
        await ctx.reply("Invalid channel id.", mention_author=False, ephemeral=True)

async def show_message(ctx : Context, channel_id : int, text_file : str):
    channel = ctx.guild.get_channel(channel_id)
    if channel:
        try:
            file = open("/home/container/messages/" + text_file)
            await channel.send(file.read())
        except OSError as exc:
            await ctx.reply("Invalid file name.", mention_author=False, ephemeral=True)
    else:
        await ctx.reply("Invalid channel id.", mention_author=False, ephemeral=True)


class AdminCommands(Cog):
    @commands.Command
    async def display_message(self, ctx : Context, text_file : str):
        await show_message(ctx, ctx.channel.id, text_file)

    @commands.Command
    async def display_attachment(self, ctx : Context, attachments : commands.Greedy[discord.Attachment]):
        await show_message_attachment(ctx, ctx.channel.id, attachments)

    @commands.Command
    async def message(self, ctx : Context, channel_id : int, *, words : str):
        channel = ctx.guild.get_channel(channel_id)
        if channel:
            await channel.send(words)
        else:
            await ctx.reply("Invalid channel id.", mention_author=False, ephemeral=True)


    @commands.Command
    async def send_message(self, ctx : Context, channel_id : int, text_file : str):
        await show_message(ctx, channel_id, text_file)

    @commands.Command
    async def send_attachment(self, ctx : Context, channel_id : int, attachments : commands.Greedy[discord.Attachment]):
        await show_message_attachment(ctx, channel_id, attachments)

    async def cog_check(self, ctx) -> bool:
        if ctx.guild.id != configreader.admin_guild_id:
            print(f"User: {ctx.author} Id: {ctx.author.id} tried to send a message or use a command in an invalid guild!")
            raise discord.ext.commands.GuildNotFound("")
        if ctx.permissions.administrator:
            return True
        raise discord.ext.commands.MissingPermissions(list(""))

    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, discord.ext.commands.GuildNotFound):
            await ctx.send("You cannot use this in an invalid guild.", ephemeral=True)
            return
        if isinstance(error, discord.ext.commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

