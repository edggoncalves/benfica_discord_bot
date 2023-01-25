import discord
from discord.ext import commands

import configuration
import covers
import next_match
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure bot
intents = discord.Intents.default()
intents.message_content = True
description = 'Um bot para obter capas de jornais.'
bot = commands.Bot(command_prefix='!', description=description, intents=intents)

# Get params
config = configuration.read()
channel_id = int(config['channel']['id'])
token = config['auth']['token']
hour = config['schedule']['hour']


@bot.command()
async def capas(message):
    for capa in covers.sports_covers():
        await message.send(capa)


@bot.command()
async def quanto_falta(message):
    await message.send(next_match.how_long_until())


@bot.command()
async def quando_joga(message):
    await message.send(next_match.when_is_it())


async def daily_covers():
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
