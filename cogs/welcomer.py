import discord
from discord.ext import commands

SEPERATOR_ROLE_IDS = [1544700530071175278, 1544700725227954187, 1544701466256613541]

class Welcomer_Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.welcome_channel_id = bot.config.get_value('welcomer.channel_id')

    @commands.Cog.listener(name="on_message")
    async def test_listener(self, message: discord.Message):
        if message.content.lower() == "this is a very specific sentence that triggers the welcome message" and not message.author.bot:
            self.bot.dispatch("member_join", message.author)  # Trigger the on_member_join event with the message author

    @commands.Cog.listener(name="on_member_join")
    async def welcome_listener(self, member: discord.Member):
        welcome_channel = self.bot.get_channel(self.welcome_channel_id)
        if welcome_channel and welcome_channel.guild == member.guild:
            embed = discord.Embed(title="Welcome!", description=f"Welcome to the server, {member.mention}!\n\nPlease read the rules and verify yourself in <#1479892302519468072>.", color=0x00FF00)
            asset_filename = "assets/salt_l2d_nobg.gif"
            dc_file = discord.File(asset_filename, filename="salt_welcome.gif")
            embed.set_image(url="attachment://salt_welcome.gif")
            embed.set_footer(text="Thank you for joining!", icon_url=member.display_avatar.url)
            await welcome_channel.send(embed=embed, file=dc_file)

            # Add separator roles to the new member
            for role_id in SEPERATOR_ROLE_IDS:
                role = member.guild.get_role(role_id)
                if role:
                    await member.add_roles(role, reason="Add separator roles on join")

    @commands.Cog.listener(name="on_member_remove")
    async def farewell_listener(self, member: discord.Member):
        welcome_channel = self.bot.get_channel(self.welcome_channel_id)
        if welcome_channel and welcome_channel.guild == member.guild:
            embed = discord.Embed(title="Goodbye!", description=f"{member.mention} has left the server.", color=0xFF0000)
            await welcome_channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcomer_Cog(bot))