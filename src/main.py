import asyncio
import os

import discord
import yaml
from discord.ext import commands
from discord.ext.commands import Bot

import nightfall_discord

if __name__ == '__main__':
    bot_intents = discord.Intents.none()
    bot_intents.message_content = True
    bot_intents.messages = True
    bot_intents.dm_messages = True
    bot_intents.guilds = True
    bot_intents.members = True

    bot = Bot(
        command_prefix="!",
        intents=bot_intents,
        help_command=commands.DefaultHelpCommand(),
    )

    path = 'bot-config.yml'

    if os.path.isfile(path):
        with open(path, 'r') as file:
            config = yaml.safe_load(file)
        bot_token = config['token']
        asyncio.run(nightfall_discord.load(bot))
        bot.run(bot_token)
    else:
        print("No config provided, unable to start bot (Please create a bot-config.yml)!")


