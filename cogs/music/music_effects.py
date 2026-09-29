import discord
from discord import app_commands
from discord.ext import commands

import wavelink
from typing import Literal

async def preset_filters(player, preset):
    filters = player.filters
    if preset == "Muffle":
        filters.low_pass.set(smoothing=50.0)
    elif preset == '8D':
        filters.rotation.set(rotation_hz=0.2)
    elif preset == 'Vaporwave':
        filters.timescale.set(pitch=0.8, speed=0.8, rate=1)
    elif preset == 'Nightcore':
        filters.timescale.set(pitch=1.15, speed=1.1, rate=1)
    elif preset == 'Karaoke':
        filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)

    await player.set_filters(filters)
    

class MusicEffectsv2(app_commands.Group):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(name='effects', description='Music Effects')

    async def interaction_check(self, inter):
        player: wavelink.Player = inter.guild.voice_client
        if not player:
            await inter.response.send_message(embed=discord.Embed(description="Bot is not connected to any voice channel", color=0xff0000), ephemeral=True)
            return False
        if not inter.user.voice.channel:
            await inter.response.send_message(embed=discord.Embed(description="You are not connected to any voice channel", color=0xff0000), ephemeral=True)
            return False
        return True

    @app_commands.command(name='presets')
    async def preset(self, inter: discord.Interaction, preset:Literal['Muffle', '8D', 'Vaporwave', 'Nightcore', 'Karaoke']):
        """Change the preset of the player."""
        player: wavelink.Player = inter.guild.voice_client
        if not player:
            return await inter.response.send_message("Bot is not connected to any voice channel", ephemeral=True)

        await preset_filters(player, preset)
        
        await inter.response.send_message(f"Changed the preset to **{preset}**.")

    @app_commands.command(name='reset', description='Reset all effects to default')
    async def reset_filter(self, inter: discord.Interaction):
        player: wavelink.Player = inter.guild.voice_client

        filters = player.filters
        filters.reset()
        await player.set_filters(filters)

        await inter.response.send_message(embed=discord.Embed(description="Reset all effects to default", color=0xca5cdd))

    '''
    @app_commands.command(name='custom', description='Set your own effects on certain aspects of the player')
    async def custom_filter(self, inter: discord.Interaction, filter:Literal['Band Filter', 'Low Pass', 'Rotation', 'Timescale', 'Tremolo', 'Vibrato', 'Distortion']):
        await inter.response.send_message('Soon')
    '''
    


async def setup(bot):
    return