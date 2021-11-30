import discord
import covers


client = discord.Client()
token = open('token', 'r').read()


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
