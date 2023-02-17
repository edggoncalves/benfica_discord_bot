import discord
from discord.ext import commands

import configuration
import covers
from next_match import SLB, PULHAS, update_match_date, generate_event, how_long_until, when_is_it
import totw

from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure bot
intents = discord.Intents.default()
intents.message_content = True
description = "Um bot para obter capas de jornais."
bot = commands.Bot(command_prefix="!", description=description, intents=intents)

# Get params
config = configuration.read()
channel_id = int(config["channel"]["id"])
token = config["auth"]["token"]
hour = config["schedule"]["hour"]

last_run = dict()
COMANDOS = (
    f"{PULHAS} Instruções:\n"
    f"`!capas` - Lista as capas dos três grandes jornais de desporto (https://24.sapo.pt/jornais/desporto)\n"
    f"`!quanto_falta` - Contagem decrescente para o próximo jogo do {SLB}\n"
    f"`!quando joga` - Dados sobre o próximo jogo do {SLB}\n"
    f"`!actualizar_data` - Actualiza os dados do bot\n"
    f"`!evento` - Gera um bloco de texto para criar eventos no servidor\n"
    f"`!pulha_comandos` - Imprime esta droga.\n"
)


@bot.command()
async def capas(message):
    last_run[datetime.now().month] = datetime.now().day
    for capa in covers.sports_covers():
        await message.send(capa)


@bot.command()
async def quanto_falta(message):
    await message.send(how_long_until())


@bot.command()
async def quando_joga(message):
    await message.send(when_is_it())


@bot.command()
async def actualizar_data(message):
    update_match_date()
    await message.send("Data do jogo actualizada. Testa com `!quando_joga` ou `!quanto_falta`")


@bot.command()
async def evento(message):
    await message.send(generate_event())


@bot.command()
async def equipa_semana(message):
    _file = totw.fetch_team_week()
    await message.send(file=_file)


@bot.command()
async def pulha_comandos(message):
    await message.send(COMANDOS)


async def daily_covers():
    n = {datetime.now().month: datetime.now().day}
    if last_run and last_run == n:
        pass
    else:
        channel = bot.get_channel(channel_id)
        for capa in covers.sports_covers():
            await channel.send(capa)


async def update_match_datetime():
    update_match_date()
    try:
        cid = int(config["schedule"]["id"])
        channel = bot.get_channel(cid)
        await channel.send("Data do jogo actualizada. Testa com `!quando_joga` ou `!quanto_falta`")
    except KeyError:
        pass


@bot.event
async def on_ready():
    await update_match_datetime()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_covers, CronTrigger(hour=hour))
    scheduler.add_job(update_match_datetime, CronTrigger(hour=hour))
    scheduler.start()


bot.run(token)
