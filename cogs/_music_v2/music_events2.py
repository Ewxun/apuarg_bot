import discord
from discord.ext import commands

import random
import time

import lava_lyra

from .music2 import QueuedPlayer

def colon_time(millis:int) -> str:
    seconds=(millis/1000)%60
    minutes=(millis/(1000*60))%60
    hours=(millis/(1000*60*60))%24
    if hours >= 1:
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    else:
        return "%02d:%02d" % (minutes, seconds)
    
def track_load_bar(player, track, length=20):
    loaded = '='
    unloaded = '-'
    
    track_started = player.current_start
    track_played = int(time.time()) - track_started
    played_percent = (track_played/int(track.length/1000)) * 100
    
    percent = max(0, min(100, played_percent))
    filled_length = int(length * percent // 100)
    bar = loaded * (filled_length - 1) + 'O' + unloaded * (length - filled_length)
    text = colon_time(track_played*1000) + '`{' + bar + '}`' + colon_time(track.length)
    return text

def text_splitter(text, split_length):
    num_of_fields = len(text)//split_length + 1
    splitlist = []
    for i in range(num_of_fields):
        splitlist.append(text[i*split_length:i+1*split_length])
    return splitlist

class PlayerToolbarView(discord.ui.View):
    def __init__(self, player):
        super().__init__(timeout=None)
        self.player : QueuedPlayer = player
        
    @discord.ui.button(emoji="⏯️", custom_id="player_toolbar:playpause", style=discord.ButtonStyle.gray, row=0)
    async def toolbar_playpause(self, inter, button):
        await self.player.pause(not self.player.paused)
        await inter.response.send_message(embed=discord.Embed(description=f"{inter.user.mention}: Paused the player." if self.player.paused else f"{inter.user.mention}: Resumed the player.", color=0xca5cdd))
        
    @discord.ui.button(emoji="⏭️", custom_id="player_toolbar:next", style=discord.ButtonStyle.gray, row=0)
    async def toolbar_next(self, inter, button):
        await self.player.skip(force=True)
        await inter.response.send_message(embed=discord.Embed(description=f"{inter.user.mention}: Skipped the current song.", color=0xca5cdd))
        
    @discord.ui.button(emoji="⏹️", custom_id="player_toolbar:stop", style=discord.ButtonStyle.red, row=0)
    async def toolbar_stop(self, inter, button):
        self.player.autoplay = False  # Remember to disable autoplay when stopping the player if not I'll keep playing a new recommended song after the queue is cleared
        self.player.queue.clear()
        await self.player.stop()
        return await inter.response.send_message(embed=discord.Embed(description=f"{inter.user.mention}: Stopped the player", color=0xca5cff))
    
    @discord.ui.button(emoji="🔁", custom_id="player_toolbar:loop", style=discord.ButtonStyle.gray, row=0)
    async def toolbar_loop(self, inter, button):
        if self.player.queue.get_loop_mode() is None:
            self.player.queue.set_loop_mode(lava_lyra.LoopMode.TRACK)
            await inter.response.send_message(embed=discord.Embed(description=f"{inter.user.mention}: Player now looping current song.", color=0xca5cdd))
        else:
            self.player.queue.disable_loop()
            await inter.response.send_message(embed=discord.Embed(description=f"{inter.user.mention}: Player no longer looping song.", color=0xca5cdd))
        

class MusicEvents_2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.backup_queue = None

    @commands.Cog.listener(name='on_lyra_node_connected')
    async def node_ready(self, node_id, is_nodelink, reconnected):
        print(f"[Music] Wavelink Node connected: {node_id} | Resumed: {reconnected} | Is Nodelink: {is_nodelink}")
        

    @commands.Cog.listener(name="on_lyra_track_start")
    async def track_start(self, player, track):
        
        # Don't count itself
        if len(player.channel.members)-1 == 0:
            await player.home.send(embed=discord.Embed(description='Disconnecting due to empty channel...'))
            await player.destroy()
            return
        
        player.current_start = int(time.time())
        self.bot.backup_queue = player.queue.copy()  # Backup the queue in case of a node crash

        embed: discord.Embed = discord.Embed(title="Now Playing", color=random.randint(0, 0xffffff))
        embed.description = f"**{track.title}** by **{track.author}**\n\n{track_load_bar(player, track)}"

        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        await player.home.send(embed=embed, view=PlayerToolbarView(player))

    @commands.Cog.listener(name="on_lyra_track_exception")
    async def track_exception(self, exception_payload, player, track):
        lavalink_exception = exception_payload.exception
        print(f"[Music] Track Exception: Cause: {exception_payload.cause} | Message: {exception_payload.message} | Severity: {exception_payload.severity} | Track: {track.title}")

        if "AllClientsFailedException" in str(lavalink_exception):
            await player.home.send(embed=discord.Embed(description=f"An error occurred while playing the track: {track.title}\nError: `All clients failed to play track due to rate limits.`", color=0xff0000))
        else:
            await player.home.send(embed=discord.Embed(description=f"An error occurred while playing the track: {track.title}\nError: \n```\n{str(lavalink_exception)[:300]}\n```", color=0xff0000))  # First 300 characters of the exception message


    @commands.Cog.listener(name="on_lyra_track_end")
    async def track_end(self, player, reason, track):
        # If autoplay is enabled, we don't want to send a message about the queue being empty after every song ends
        if len(player.queue) == 0 and player.autoplay == False and reason == "finished":
            await player.home.send(embed=discord.Embed(description="Queue is empty...", color=0x0000ff))
            return


async def setup(bot):
    await bot.add_cog(MusicEvents_2(bot))