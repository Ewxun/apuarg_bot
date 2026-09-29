import os
import traceback

from discord import app_commands
import discord
from discord.ext import commands

class HotReload(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @app_commands.command(name='reload', description='Reload all cogs')
  async def reload(self, interaction):
    if interaction.user.id not in self.bot.owner_ids:
        return await interaction.response.send_message("Missing Permissions: `Bot Owner`", ephemeral=True)

    await interaction.response.defer(thinking=True)
    for filename in os.listdir('cogs'):
        if filename.startswith("_"):
            continue
        if filename.endswith('.py'):
            try:
                await self.bot.reload_extension(f'cogs.{filename[:-3]}')
                print(f"[Cogs] Reloaded {filename[:-3]}")
            except Exception as err:
                err_tb = traceback.format_exception(err, value=err, tb=err.__traceback__)
                print(f'[Cogs] Unable to reload {filename[:-3]}:\n[Cogs] {"".join(err_tb)}')
        if os.path.isdir(f"cogs/{filename}"):
            for dir_file in os.listdir(f'cogs/{filename}'):
                if dir_file.startswith("_"):
                    continue
                if dir_file.endswith('.py'):
                    try:
                        await self.bot.reload_extension(f'cogs.{filename}.{dir_file[:-3]}')
                        print(f"[Cogs] Reloaded {filename}.{dir_file[:-3]}")
                    except Exception as err:
                        err_tb = traceback.format_exception(err, value=err, tb=err.__traceback__)
                        print(f'[Cogs] Unable to reload {filename}.{dir_file[:-3]}:\n[Cogs] {"".join(err_tb)}')
    await interaction.followup.send(embed=discord.Embed(title="Success", description="All cogs reloaded successfully!", color=0x00FF00), ephemeral=True)


async def setup(bot):
  await bot.add_cog(HotReload(bot))