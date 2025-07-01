import os
import asyncio

TOKEN = os.environ.get('DISCORD_TOKEN')
asyncio.run(bot.start(TOKEN))
