import asyncio
import discord
from discord.ext import commands, tasks

from tgtg import TgtgClient

import os
from dotenv import load_dotenv
from checker import CheckerCog

# Gets discrord server information from the .env
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
ANNOUNCEMENTS_CHANNEL = os.getenv('CHANNEL_ANOUNCEMENTS')

# Initializes the discord bot
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
tgtg_client = None
myChecker = None

###############################################################################
# Commands
###############################################################################
@bot.command(name='test', help='Very important message')
async def test_msg(ctx):
    response = "TEST: etucsim"
    await ctx.send(response)

@bot.command(name="add", help='Format: `!add <url>[,<url>,<url>,...]`')
async def add_reminder(ctx: commands.Context, arg: str):
    global myChecker, tgtg_client
    for url in arg.split(','):
        await ctx.send( await myChecker.add_reminder(tgtg_client, ctx.message.author, url) )

@bot.command(name="reminders", help="Format: `!reminders` to get indecies")
async def check_user_rem(ctx: commands.Context):
    global myChecker
    user_rems = await myChecker.get_user_with_time_rems(ctx.message.author)
    if len(user_rems) > 0:
        await ctx.send( '\n'.join( str(i) + ". " + rem for i, rem in enumerate(user_rems, 1) ) )
    else:
        await ctx.send( "Error - No reminders are set..." )

@bot.command(name="remove", help="Format: `!remove <index>`")
async def remove_reminder(ctx: commands.Context, arg: str):
    global myChecker
    await ctx.send( await myChecker.remove_reminder(ctx.message.author, arg) )

@bot.command(name="removeall", help="Format: `!removeall`")
async def remove_all_rems(ctx: commands.Context):
    global myChecker
    await ctx.send( await myChecker.remove_all_user_rems(ctx.message.author) )

@bot.command(name="info", help="Format: `!info <index>`")
async def info_of_reminder(ctx: commands.Context, arg: str):
    global myChecker
    await ctx.send( await myChecker.get_rem_info_idx(ctx.message.author, arg) )

@bot.command(name="check", help="Format: `!check <url>`")
async def check_a_url(ctx: commands.Context, arg: str):
    global myChecker, tgtg_client
    await ctx.send( await myChecker.get_rem_info_url(tgtg_client, ctx.message.author, arg) )

@bot.command(name="debug", help="Format: `!debug <index>`")
async def info_of_reminder(ctx: commands.Context, arg: str):
    global myChecker
    await ctx.send( await myChecker.get_rem_debug(ctx.message.author, arg) )
             
@bot.command(name="logged_in", help="Used to confirm no issues with tgtg client")
async def check_login_token(ctx: commands.Context):
    global myChecker
    await ctx.send( await myChecker.check_login_token() )

@bot.command(name="get_all", help="Get a comma seperated string of everything you've added.")
async def get_all_for_later(ctx: commands.Context):
    global myChecker
    await ctx.send( await myChecker.get_repostable_for_user(ctx.message.author) )

@bot.command()
async def shutdown(ctx):
    # TODO: Save existing reminders to database befor quitting
    
    global myChecker
    for user in bot.get_guild( int(GUILD) ).members:
        msg = await myChecker.get_repostable_for_user(user)
        if msg != "":
            await ctx.send( msg )

    myChecker.task_end()
    exit(0)

###############################################################################
# Events
###############################################################################
@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.event
async def on_ready():
    guild = bot.get_guild( int(GUILD) )
    print(
        f'{bot.user} focusing on the following guild:\n'
        f'{guild}'
    )

    # Start looping task
    global myChecker, tgtg_client
    tgtg_client = TgtgClient(access_token=os.getenv('access_token'), 
                             refresh_token=os.getenv('refresh_token'), 
                             user_id=os.getenv('user_id'),
                             cookie=os.getenv('cookie'))
    myChecker = CheckerCog(bot, tgtg_client, 
                           bot.get_guild( int(GUILD) ).get_channel( int(ANNOUNCEMENTS_CHANNEL) ))
    
    # Load in from database all reminders

async def main():
    # start the client
    async with bot:
        await bot.start(DISCORD_TOKEN)

asyncio.get_event_loop().run_until_complete(main())
