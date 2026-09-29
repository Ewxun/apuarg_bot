import discord
from discord.ext import commands


class HoneyPot_Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.honeypot_channel_id = bot.config.get_value('honeypot.channel_id')
        self.ghost_role_id = bot.config.get_value('honeypot.ghost_role_id')

    @commands.Cog.listener(name="on_message")
    async def honeypot_listener(self, message: discord.Message):
        if message.content.strip() == ">>setup_honeypot":
            embed = discord.Embed(description="# (THIS IS A TEST) Warning!\n# DO NOT SEND MESSAGES HERE\nYou will be banned for sending messages here.\n\n-# ⚠️ Committee members included", color=0xFF0000)
            embed.set_thumbnail(url="https://images.icon-icons.com/1465/PNG/512/564honeypot_101018.png")
            dc_file = discord.File("assets/miku_ooo.jpg", filename="miku.jpg")
            embed.set_image(url="attachment://miku.jpg")
            embed.set_footer(text="This channel is being monitored for spam and bot activity. Miku is watching you.")
            await message.channel.send(embed=embed, file=dc_file)
            return 

        if message.channel.id == self.honeypot_channel_id and not message.author.bot and message.author.id not in self.bot.owner_ids:
            await message.delete()
            if self.ghost_role_id:
                ghost_role = discord.utils.get(message.guild.roles, id=self.ghost_role_id)
                if ghost_role:
                    await message.author.add_roles(ghost_role)
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(HoneyPot_Cog(bot))