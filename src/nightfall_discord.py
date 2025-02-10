import os

import yaml
from discord.ext.commands import Bot

from configreader import ConfigReader
from gamestatuswatch import GameStatusWatch
from user_admin_interactions import DirectMessageHandler, ThreadHandler

loadedcogs = list()
nf_bot = Bot

async def load(bot: Bot):
    await bot.load_extension("nightfall_discord")


async def setup(bot: Bot):
    print(f"Loading Nightfall Discord.")
    global nf_bot
    nf_bot = bot
    path = 'bot-config.yml'
    print(f"Loading {path}")
    if os.path.isfile(path):
        with open(path, 'r') as file:
            config = yaml.safe_load(file)

        bot_config = ConfigReader(config)

        # Add all cogs into a list
        loadedcogs.insert(0, GameStatusWatch(bot, bot_config))
        loadedcogs.insert(1, DirectMessageHandler(bot, bot_config))
        loadedcogs.insert(2, ThreadHandler(bot, bot_config))


    # Add all cogs in the list to the bot
        for cog in loadedcogs:
            await bot.add_cog(cog)

        print(f"Successfully loaded Nightfall Discord!")
    else:
        print(f"No config provided, unable to start bot (Please create a {path})!")
        await bot.close()


async def teardown(bot: Bot):
    print(f"Disabling Nightfall Discord.")
    # Remove all cogs in the list from the bot.
    for cog in loadedcogs:
        await bot.remove_cog(cog)
    print(f"Successfully disabled Nightfall Discord")