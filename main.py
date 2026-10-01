import os
import traceback

import discord
from discord import app_commands
from discord.ext import commands

from ext import config


token = config.get_value('bot.token')
bot_owners = config.get_value('bot.bot_owners')
sync_guilds = config.get_value('bot.presync_guilds')

async def loadcogs():
    print("[Cogs] Loading all cogs...")
    for filename in os.listdir('cogs'):
        if filename.startswith("_"):
            continue
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"[Cogs] Loaded {filename[:-3]}")
            except Exception as err:
                err_tb = traceback.format_exception(err, value=err, tb=err.__traceback__)
                print(f'[Cogs] Unable to load {filename[:-3]}:\n[Cogs] {"".join(err_tb)}')
        if os.path.isdir(f"cogs/{filename}"):
            for dir_file in os.listdir(f'cogs/{filename}'):
                if dir_file.startswith("_"):
                    continue
                if dir_file.endswith('.py'):
                    try:
                        await bot.load_extension(f'cogs.{filename}.{dir_file[:-3]}')
                        print(f"[Cogs] Loaded {filename}.{dir_file[:-3]}")
                    except Exception as err:
                        err_tb = traceback.format_exception(err, value=err, tb=err.__traceback__)
                        print(f'[Cogs] Unable to load {filename}.{dir_file[:-3]}:\n[Cogs] {"".join(err_tb)}')
    print("[Cogs] All Cogs Loaded!")

async def sync_slashes(guild_ids):
    for g_id in guild_ids:
        snowf_obj = discord.Object(id=g_id)
        bot.tree.copy_global_to(guild=snowf_obj)
        await bot.tree.sync(guild=snowf_obj)
        print(f"[Slash CMD] Synced Commands - {g_id}")
    print("[Slash CMD] All commands synced")


class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(
          command_prefix = "!-=",
          case_insensitive=True,
          strip_after_prefix=True,
          owner_ids=list(set(bot_owners)),
          intents=intents
        )

    async def setup_hook(self):
        await loadcogs()
        await sync_slashes(sync_guilds)


bot = MyClient(intents=discord.Intents().all())
bot.config = config


#------------------------
@bot.event
async def on_ready():
    print(f"[Client] Bot connected successfully as {str(bot.user)}")
       
    activity = discord.Activity(type=discord.ActivityType.listening, name="Echoes of Memoria - Lucidin")
    await bot.change_presence(activity=activity)

@bot.event
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

#------------------------
@bot.tree.command(description="Get latency info from Discord")
async def ping(inter):
    embed = discord.Embed(title="Pong!", color=0xca5cdd)
    embed.add_field(name='Latency', value=f"`{round(bot.latency*1000, 2)}` ms", inline=False)
    if inter.guild.voice_client:
        vc_ping = inter.guild.voice_client.ping
        if vc_ping != 0 or vc_ping != None:
            embed.add_field(name='Voice Channel Latency', value=f"Latency: `{vc_ping}` ms")
    await inter.response.send_message(embed=embed)
    
@ping.error
async def ping_error(inter, error):
    embed = discord.Embed(title='An error occured.', description='This is a rare error please inform @ewxun with the following error message', color=0xff0000)
    embed.add_field(name='Error', value=f'```\n{error}\n```')
    await inter.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sync", description="Sync slash commands globally. (Owner only)")
@commands.is_owner()
async def sync_commands(inter):
    await bot.tree.sync()
    await inter.response.send_message("Slash commands synced!", ephemeral=True)


class AboutView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="GitHub", url="https://github.com/Ewxun"))

    @discord.ui.button(label="Credits", style=discord.ButtonStyle.primary)
    async def credits_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Credits", color=0x00ff00)
        embed.add_field(name="People", value="<@686969234428919832> (ewxun) - Developer", inline=False)
        embed.add_field(name="Codebases", value="[discord.py](https://github.com/Rapptz/discord.py) - Discord API Wrapper", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="about", description="Display information about the bot.")
async def about(inter):
    embed = discord.Embed(title="About", description="Bot made by <@686969234428919832> (ewxun) for the APU Rhythm and Arcade Games community.\n\nAllergy warning: Contains lots of love <3", color=0x00ff00)
    await inter.response.send_message(embed=embed, view=AboutView())

bot.run(token)