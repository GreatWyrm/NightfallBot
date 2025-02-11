import os

import yaml
from discord.ext.commands import Bot

import configreader
from admin_commands import AdminCommands
from gamestatuswatch import GameStatusWatch
from user_admin_interactions import DirectMessageHandler, ThreadHandler

loadedcogs = list()
nf_bot = None

async def load(bot: Bot):
    await bot.load_extension("nightfall_discord")
    global nf_bot
    nf_bot = bot


async def setup(bot: Bot):
    print(f"Loading Nightfall Discord.")
    path = 'bot-config.yml'
    print(f"Loading {path}")
    if os.path.isfile(path):
        with open(path, 'r') as file:
            config = yaml.safe_load(file)

        configreader.readconfig(config)

        # Add all cogs into a list
        loadedcogs.insert(0, GameStatusWatch(bot))
        loadedcogs.insert(1, DirectMessageHandler())
        loadedcogs.insert(2, ThreadHandler())
        loadedcogs.insert(3, AdminCommands())


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