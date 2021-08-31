import os
import discord
from discord.ext import commands
from replit import db

bot = commands.Bot(command_prefix = '*',case_insensitive =True)

@bot.event
async def on_ready():
  for key in db.keys():
    del db[key]
  print('Bot online')

@bot.command()
async def load(ctx,extension):
  bot.load_extension(f'cogs.{extension}')
  await ctx.send("{} loaded".format(extension))
  
@bot.command()
async def unload(ctx,extension):
  bot.unload_extension(f'cogs.{extension}')
  await ctx.send("{} unloaded".format(extension))
@bot.command()
async def reload(ctx,extension):
  bot.unload_extension(f'cogs.{extension}')
  bot.load_extension(f'cogs.{extension}')
  await ctx.send("{} reloaded".format(extension))


for filename in os.listdir('./cogs'):
  if filename.endswith('.py'):
    bot.load_extension(f'cogs.{filename[:-3]}')



bot.run('YOUR TOKEN HERE')