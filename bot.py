from patcher import discord, commands
import config

discord.http.Route.BASE = config.API_BASE

bot = discord.Client()


@bot.event
async def on_ready():
    print("Connected!")


@bot.event
async def on_message(message):
    if message.content == "ping":
        await message.reply("pong")


bot.run(config.TOKEN)
