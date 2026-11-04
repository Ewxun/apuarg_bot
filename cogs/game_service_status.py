import asyncio

import discord
from discord import app_commands
from discord.ext import commands, tasks

import aiohttp

from ext import config

game_name_map = {
    "allnet": "All.Net",
    "maimai": "maimai",
    "chunithm": "CHUNITHM"
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

class GameServiceStatus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_game_service_status.start()

    status_group = app_commands.Group(name="game_status", description="Check the status of game services")

    @tasks.loop(minutes=5)
    async def check_game_service_status(self):
        update_channel_id = config.get_value('game_service_status.channel_id')
        message_id = config.get_value('game_service_status.message_id')
        game_urls = config.get_value('game_service_status.site_urls')

        game_statuses = {}
        all_operational = True

        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            for game_key, url in game_urls.items():
                game_name = game_name_map.get(game_key, game_key)
                try:
                    async with session.get(url, timeout=10, headers=headers) as response:
                        status_code = response.status
                        if status_code == 200:
                            status_color = "🟢"  # Green circle for UP
                            status_message = "Operational"
                        elif status_code == 503:
                            status_color = "🟡"  # Yellow circle for MAINTENANCE
                            status_message = "Maintenance"
                        else:
                            status_color = "🔴"  # Red circle for DOWN
                            status_message = "Down"
                            all_operational = False

                except aiohttp.ClientError:
                    status_color = "❓"
                    status_message = "Error when fetching status"
                    all_operational = False

                except asyncio.TimeoutError:
                    status_color = "🔴"
                    status_message = "Timeout"
                    all_operational = False
                except Exception:
                    status_color = "🔴"
                    status_message = "Site Error"
                    all_operational = False

                game_statuses[game_name] = [status_color, status_message]
    
        if all_operational:
            status_description = "All game services are operational."
        else:
            status_description = "Some game services are experiencing issues."

        # Add update timestamp to the description
        status_description += f"\n\nLast updated: <t:{int(discord.utils.utcnow().timestamp())}:f>\nNext update: <t:{int((discord.utils.utcnow().timestamp() + (5 * 60)))}:R>"

        # Create an embed to display the game service statuses
        embed = discord.Embed(title="Game Service Status", description=status_description, color=0xd96fd2)
        ping_icon = discord.File("assets/ping.png", filename="ping.png")
        embed.set_thumbnail(url="attachment://ping.png")

        for game_name, (status_color, status_message) in game_statuses.items():
            embed.add_field(name=game_name, value=f"{status_color} - {status_message}", inline=False)

        message_channel = self.bot.get_channel(update_channel_id)
        message = await message_channel.fetch_message(message_id)
        await message.edit(embed=embed)


    @check_game_service_status.before_loop
    async def before_check_game_service_status(self):
        await self.bot.wait_until_ready()

    @status_group.command(name="init", description="Initialize the game service status message in the specified channel.")
    async def init_status_message(self, interaction: discord.Interaction):
        channel_id = config.get_value('game_service_status.channel_id')
        channel = self.bot.get_channel(channel_id)

        await channel.send(embed=discord.Embed(title="Game Service Status", description="Initializing game service status message...", color=0xd96fd2))

        await interaction.response.send_message("Game service status message initialized successfully.", ephemeral=True)

    @status_group.command(name="refresh", description="Refresh the game service status manually.")
    async def check_status(self, interaction: discord.Interaction):
        await interaction.response.send_message("Checking game service status...", ephemeral=True)
        await self.check_game_service_status()


async def setup(bot: commands.Bot):
    await bot.add_cog(GameServiceStatus(bot))