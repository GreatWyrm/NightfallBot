from datetime import datetime, timezone, timedelta

import discord
from discord.ext import tasks, commands
from discord.ext.commands import Bot, Cog
from discord.ext.commands import has_permissions
from mcstatus import JavaServer
from mcstatus.status_response import JavaStatusResponse

from configreader import ConfigReader


#  With thanks to https://github.com/kkrypt0nn/Python-Discord-Bot-Template/ for code guidance

class GameStatusWatch(Cog):
    def __init__(self, bot : Bot, config : ConfigReader):
        self.bot = bot
        self.config = config
        self.bot_response_handler = ServerUpdateChecker(self.config.host, self.config.port,
                                                                   update_frequency=self.config.update_frequency,
                                                                   embed_color_list=self.config.embed_colors)
        self.gamewatch_pinger = GamewatchPinger(role_id=self.config.role_id, ping_cooldown=self.config.role_ping_cooldown_seconds, manual_cooldown=self.config.role_ping_manual_cooldown_seconds)
    def parse_server_status(status: JavaStatusResponse) -> str:
        latency = status.latency
        server_version = status.version.name
        player_list = status.players
        motd = status.motd.to_plain()

        return (f'Version: {server_version}\n'
                f'Latency: {round(latency)} ms\n'
                f'Players Online: {player_list.online}/{player_list.max}\n'
                f'{motd}')

    @commands.Cog.listener()
    async def on_ready(self):
        update_channel = self.bot.get_channel(int(self.config.bot_updates_channel_id))
        self.list_server_status.change_interval(minutes=self.config.update_frequency)
        self.list_server_status.start(update_channel=update_channel)
        print(f"Started periodic update with frequency of {self.config.update_frequency} minutes")

    @tasks.loop()
    async def list_server_status(self, update_channel: discord.TextChannel) -> None:
        try:
            if update_channel:  # If not none, run other code
                # Retrieve last message, if it's written by this bot, and it's an embed, let's edit it
                # Otherwise post a new message and delete the other one if it's not an embed.
                last_message_id = update_channel.last_message_id
                if last_message_id:
                    last_message: discord.Message = await update_channel.fetch_message(last_message_id)
                    if last_message.author == self.bot.user:
                        if last_message.embeds:
                            await last_message.edit(embed=self.bot_response_handler.get_periodic_update(update_channel))
                        else:
                            await last_message.delete()
                            await update_channel.send(embed=self.bot_response_handler.get_periodic_update(channel=update_channel))
                    else:
                        await update_channel.send(embed=self.bot_response_handler.get_periodic_update(channel=update_channel))
                else:
                    # Otherwise send a new message
                    await update_channel.send(embed=self.bot_response_handler.get_periodic_update(channel=update_channel))
            else:
                print("Failed to find update channel! (Wrong or missing id?)")
            await self.bot.change_presence(activity=discord.Game(self.bot_response_handler.get_player_count_string()))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as discordError:
            print(f"Failed to update server status")
            print(discordError)

    @commands.command(name="info", brief="Displays info about the bot", description="Displays the source code of the bot and who made "
                                                                  "the profile picture.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def info(self, ctx: commands.Context):
        await ctx.send(handle_info())

    @commands.command(name="gamewatch", brief="Pings Gamewatch", description="Tries to ping gamewatch, if it is off cooldown.")
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def gamewatch(self, ctx: commands.Context):
        # Verify ping channel exists
        if self.config.bot_ping_channel_id > 0:
            ping_channel = ctx.guild.get_channel(int(self.config.bot_ping_channel_id))
            if not ping_channel:
                print("Failed to find ping channel! (Wrong or missing id?)")
                return
            if ctx.channel.id != ping_channel.id:
                await ctx.channel.send(f"Cannot ping gamewatch here, must ping in <#{ping_channel.id}>.")
                return
            # Player count check
            current_online_count = self.bot_response_handler.get_player_count()
            if current_online_count < self.config.min_players_ping_threshold:
                await ctx.channel.send(f"Too few players online to ping! (Need {self.config.min_players_ping_threshold} or more "
                                       f"players, only {current_online_count} player(s) online)")
                return
            # Verify you pinged in the gamewatch role
            if self.gamewatch_pinger.can_ping_gamewatch(ctx.message.created_at):
                await self.gamewatch_pinger.send_gamewatch_ping(ctx, ping_channel, self.bot.get_channel(int(self.config.bot_updates_channel_id)))
            else:
                # Print when you can ping gamewatch again
                await self.gamewatch_pinger.send_gamewatch_on_cooldown(ctx)
        else:
            # Verify you pinged in the gamewatch role
            if self.gamewatch_pinger.can_ping_gamewatch(ctx.message.created_at):
                await self.gamewatch_pinger.send_gamewatch_ping(ctx, ctx.channel, self.bot.get_channel(int(self.config.bot_updates_channel_id)))
            else:
                # Print when you can ping gamewatch again
                await self.gamewatch_pinger.send_gamewatch_on_cooldown(ctx)

    @commands.command(name="gamewatch_cooldown", brief="Puts the Gamewatch ping on cooldown. Admin Only.", description="Puts the Gamewatch ping on a "
                                                                                       "predetermined cooldown, "
                                                                                       "requires the 'Manage Messages "
                                                                                       "permission to use.")
    @has_permissions(manage_messages=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def gamewatch_cooldown(self, ctx: commands.Context):
        await self.gamewatch_pinger.start_gamewatch_cooldown(ctx)

    @commands.command(brief="Restarts the server status updater task. Admin only.")
    @has_permissions(manage_messages=True)
    @commands.cooldown(1, 1, commands.BucketType.guild)
    async def restart_lister(self, ctx: commands.Context):
        update_channel = self.bot.get_channel(self.config.bot_updates_channel_id)
        self.list_server_status.restart(update_channel=update_channel)
        await ctx.channel.send("Restarted server updater.")

    @commands.command(name="reload_extension", brief="Restarts the Nightfall Bot. Admin only.")
    @commands.has_role("Admin")
    async def reload_extension(self, ctx: commands.Context):
        await ctx.channel.send("Reloading the Nightfall Bot.")
        await self.bot.reload_extension("nightfall_discord")

    async def cog_check(self, ctx) -> bool:
        if ctx.guild.id != self.config.bot_reports_guild_id:
            print(f"User: {ctx.author} Id: {ctx.author.id} tried to send a message or use a command in an invalid guild!")
            raise discord.ext.commands.GuildNotFound("")
        return True

    async def cog_command_error(self, ctx, error: Exception) -> None:
        if isinstance(error, discord.ext.commands.GuildNotFound):
            await ctx.send("You cannot use this in an invalid guild.")
            return


class ServerUpdateChecker:
    def __init__(self, host, port, update_frequency, embed_color_list):
            self.hostaddress = "{host}:{port}".format(host=host, port=port)
            self.update_frequency = update_frequency
            self.embed_color_list = embed_color_list

    def get_periodic_update(self, channel: discord.TextChannel) -> discord.Embed:
        nf_server = JavaServer.lookup(self.hostaddress)
        status = nf_server.status()
        server_version = status.version.name
        motd_lowercase = status.motd.to_plain().lower()
        player_list = status.players
        color = 0xFFFFFF
        for embed_color_obj in self.embed_color_list:
            if ('keyword' in embed_color_obj and "color" in embed_color_obj
                    and embed_color_obj["keyword"] in motd_lowercase):
                color = embed_color_obj["color"]
                break

        embed = discord.Embed(title=f"Nightfall - {server_version}", color=color, description=status.motd.to_plain())
        embed.set_author(name="Nightfall Bot")
        embed.set_thumbnail(url=channel.guild.icon.url)
        update_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        embed.set_footer(text=f"Updated on {update_time}. Updates every {self.update_frequency} minute(s).")
        embed.add_field(name="Players Online", value=f"{player_list.online}/{player_list.max}")

        return embed

    def get_player_count_string(self) -> str:
        nf_server = JavaServer.lookup(self.hostaddress)
        status = nf_server.status()
        player_list = status.players
        return f'Players Online: {player_list.online}/{player_list.max}'

    def get_player_count(self) -> int:
        nf_server = JavaServer.lookup(self.hostaddress)
        status = nf_server.status()
        return status.players.online


class GamewatchPinger:
    def __init__(self, role_id: int, ping_cooldown: int, manual_cooldown: int):
        self.last_gamewatch_ping = datetime.now(timezone.utc) - timedelta(hours=1)
        self.role_id = role_id
        # In seconds
        self.ping_cooldown = ping_cooldown
        # In seconds
        self.manual_cooldown = manual_cooldown

    def can_ping_gamewatch(self, created_at: datetime):

        # Has enough time passed?
        delta = created_at - (self.last_gamewatch_ping + timedelta(seconds=self.ping_cooldown))
        return delta.total_seconds() > 0

    async def send_gamewatch_ping(self, ctx: commands.Context, ping_channel: discord.TextChannel,
                                  update_channel: discord.TextChannel):
        try:
            role = ctx.guild.get_role(self.role_id)
            if role:
                lastmessageid = update_channel.last_message_id
                if lastmessageid:
                    message = await update_channel.fetch_message(lastmessageid)
                    if message.author.bot and message.embeds:
                        await ctx.reply(
                            content=f"{ctx.author.name} has pinged Gamewatch, {role.mention}\n{message.jump_url}",
                            embeds=message.embeds,
                            mention_author=False
                        )
                else:
                    await ping_channel.send("No status message found!")

                self.last_gamewatch_ping = datetime.now(timezone.utc)
            else:
                await ping_channel.send("Gamewatch was pinged, but bot failed to find role!")
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as discordError:
            print(f"Failed to update server status")
            print(discordError)

    async def send_gamewatch_on_cooldown(self, ctx: commands.Context):
        delta = (self.last_gamewatch_ping + timedelta(seconds=self.ping_cooldown)) - ctx.message.created_at
        # Cooldown: message created at - (last_ping_time + ping cooldown time) gives seconds until next ping
        await ctx.channel.send(
            f"Gamewatch is on cooldown! You can ping again in {round(delta.total_seconds())} seconds.")

    async def start_gamewatch_cooldown(self, ctx: commands.Context):
        # Set last gamewatch ping to now, plus the delta we want to supress, minus the delta of the standard ping
        # cooldown to get things to line up
        self.last_gamewatch_ping = datetime.now(timezone.utc) + timedelta(seconds=self.manual_cooldown) - timedelta(
            seconds=self.ping_cooldown)
        available_time = self.last_gamewatch_ping.strftime("%m/%d/%Y, %H:%M:%S")
        await ctx.channel.send(f"{ctx.author.name} has put Gamewatch on cooldown for {self.manual_cooldown} seconds. "
                               f"Next ping time is {available_time} UTC.")

def handle_info() -> str:
    return "Code: https://github.com/GreatWyrm/NightfallBot\nProfile Picture made by Skylarr"