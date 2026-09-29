import discord
from discord.ext import commands
from discord import app_commands

class Starboard_Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.starboard_channel_id = bot.config.get_value('starboard.channel_id')
        self.starboard_emoji = "⭐"
        self.starboard_threshold = bot.config.get_value('starboard.threshold')

    starboard_group = app_commands.Group(name="starboard", description="Starboard commands")

    @commands.Cog.listener(name="on_reaction_add")
    async def starboard_listener(self, reaction: discord.Reaction, user: discord.User):
        if reaction.message.guild is None or user.bot or reaction.message.channel.id != self.starboard_channel_id:
            return
        if str(reaction.emoji) == self.starboard_emoji and reaction.count >= self.starboard_threshold:
            starboard_channel = self.bot.get_channel(self.starboard_channel_id)
            if starboard_channel:
                embed = discord.Embed(title="Starred Message", description=reaction.message.content, color=0xFFD700)
                embed.set_author(name=reaction.message.author.display_name, icon_url=reaction.message.author.avatar.url)
                embed.add_field(name="Jump to Message", value=f"[Click Here]({reaction.message.jump_url})")
                await starboard_channel.send(embed=embed)
            

    @starboard_group.command(name="channel", description="Set the starboard channel")
    async def set_sb_channel(self, inter: discord.Interaction, channel: discord.TextChannel):
        self.starboard_channel_id = channel.id
        await inter.response.send_message(f"Starboard channel set to {channel.mention}!")

    @starboard_group.command(name="emoji", description="Set the starboard emoji")
    async def set_sb_emoji(self, inter: discord.Interaction, emoji: str):
        self.starboard_emoji = emoji
        await inter.response.send_message(f"Starboard emoji set to {emoji}!")

    @starboard_group.command(name="threshold", description="Set the starboard threshold")
    async def set_sb_threshold(self, inter: discord.Interaction, threshold: int):
        self.starboard_threshold = threshold
        await inter.response.send_message(f"Starboard threshold set to **{threshold}**!")

async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard_Cog(bot))