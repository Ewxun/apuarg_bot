import discord
from discord.ext import commands, tasks
import aiohttp

from ext import config

# Sensitive Private API, do not share
# John Sega will be mad if you poke around too much
from ext import all_net_api

class SegaNewsUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_sega_news.start()

    @tasks.loop(minutes=60)
    async def check_sega_news(self):
        async with aiohttp.ClientSession() as session:
            new_pop_urls = await all_net_api.fetch_news(session)

        if len(new_pop_urls) > 0:
            for game, pop_url in new_pop_urls:
                channel_id = config.get_value(f'sega_news.news_channels.{game}')
                channel: discord.TextChannel = self.bot.get_channel(channel_id)

                if channel:
                    image_bytes_list = await all_net_api.generate_png(session, pop_url)
                    file_list = []
                    for i, image_bytes in enumerate(image_bytes_list):
                        file = discord.File(fp=image_bytes, filename=f"{game}_news_{i}.png")
                        file_list.append(file)
                    
                    await channel.send(files=file_list)
                else:
                    print(f"[Sega News] Channel with ID {channel_id} not found.")
        return

async def setup(bot):
    await bot.add_cog(SegaNewsUpdate(bot))