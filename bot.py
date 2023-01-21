import discord
from discord.ext import commands

import configparser
import covers
from os import path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# Configure bot
intents = discord.Intents.default()
intents.message_content = True
description = 'Um bot para obter capas de jornais.'
bot = commands.Bot(command_prefix='!', description=description, intents=intents)

# Get params
base_path = path.dirname(__file__)
relative_path = 'discord.conf'
config_path = path.join(base_path, relative_path)
config = configparser.ConfigParser()
config.read(config_path)
channel_id = int(config['channel']['id'])
token = config['auth']['token']
hour = config['schedule']['hour']
last_run = dict()


@bot.command()
async def capas(message):
    last_run[datetime.now().month] = datetime.now().day
    for capa in covers.sports_covers():
        await message.send(capa)


async def daily_covers():
    n = {datetime.now().month: datetime.now().day}
    if last_run and last_run == n:
        pass
    else:
        channel = bot.get_channel(channel_id)
        for capa in covers.sports_covers():
            await channel.send(capa)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_covers, CronTrigger(hour=hour))
    scheduler.start()


bot.run(token)
