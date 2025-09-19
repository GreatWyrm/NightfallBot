from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from mcstatus import JavaServer
from mcstatus.status_response import JavaStatusResponse


#  https://github.com/py-mine/mcstatus

def parse_server_status(status: JavaStatusResponse) -> str:
    latency = status.latency
    server_version = status.version.name
    player_list = status.players
    motd = status.motd.to_plain()

    return (f'Version: {server_version}\n'
            f'Latency: {round(latency)} ms\n'
            f'Players Online: {player_list.online}/{player_list.max}\n'
            f'{motd}')


def handle_info() -> str:
    return "Code: https://github.com/GreatWyrm/NightfallBot\nProfile Picture made by Skylarr"


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
        embed.add_field(name="w/ ", value=f"{player_list.online} players")

        return embed

    def get_player_count_string(self) -> str:
        nf_server = JavaServer.lookup(self.hostaddress)
        status = nf_server.status()
        player_list = status.players
        return f'Players Online: {player_list.online}'

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
        role = ctx.guild.get_role(self.role_id)
        if role:
            lastmessageid = update_channel.last_message_id
            if lastmessageid:
                message = await update_channel.fetch_message(lastmessageid)
                if message.author.bot and message.embeds:
                    await ctx.reply(
                        content=f"{ctx.author.name} has pinged {role.mention}\n{message.jump_url}",
                        embeds=message.embeds,
                        mention_author=False
                    )
            else:
                await ping_channel.send("No status message found!")

            self.last_gamewatch_ping = datetime.now(timezone.utc)
        else:
            await ping_channel.send("Gamewatch was pinged, but bot failed to find role!")

    async def send_gamewatch_on_cooldown(self, ctx: commands.Context):
        delta = (self.last_gamewatch_ping + timedelta(seconds=self.ping_cooldown)) - ctx.message.created_at
        # Cooldown: message created at - (last_ping_time + ping cooldown time) gives seconds until next ping
        await ctx.channel.send(
            f"Gamewatch is on cooldown! You can ping in {round(delta.total_seconds())} seconds.")

    async def start_gamewatch_cooldown(self, ctx: commands.Context):
        # Set last gamewatch ping to now, plus the delta we want to supress, minus the delta of the standard ping
        # cooldown to get things to line up
        self.last_gamewatch_ping = datetime.now(timezone.utc) + timedelta(seconds=self.manual_cooldown) - timedelta(
            seconds=self.ping_cooldown)
        available_time = self.last_gamewatch_ping.strftime("%m/%d/%Y, %H:%M:%S")
        await ctx.channel.send(f"{ctx.author.name} has put Gamewatch on cooldown for {self.manual_cooldown} seconds. "
                               f"Next ping time is {available_time} UTC.")
