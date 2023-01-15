import discord
from discord.ext import commands

import aiocron
import configparser
import covers
from os import path

# Configure bot
intents = discord.Intents.default()
intents.message_content = True
description = 'Um bot para obter capas de jornais.'
bot = commands.Bot(command_prefix='!', description=description, intents=intents)

# Get token
base_path = path.dirname(__file__)
relative_path = 'discord.conf'
config_path = path.join(base_path, relative_path)
config = configparser.ConfigParser()
config.read(config_path)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


@bot.command()
async def capas(message):
    for capa in covers.sports_covers():
        await message.send(capa)


@aiocron.crontab('0 8 * * *')
async def daily_covers():
    for capa in covers.sports_covers():
        await bot.get_channel(int(config['channel']['id'])).send(capa)


bot.run(config['auth']['token'])
