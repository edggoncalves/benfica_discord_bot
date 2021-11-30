import os.path

import discord
import covers
from os import path


client = discord.Client()
base_path = path.dirname(__file__)
relative_path = '\\token'
token_path = os.path.join(base_path, relative_path)
token = open(token_path, 'r').read()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!capas'):
        capas = covers.sports_covers()
        for capa in capas:
            await message.channel.send(capa)

client.run(token)
