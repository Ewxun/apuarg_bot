import discord
from discord.ext import commands

import random
import time
from urllib.parse import quote

import aiohttp
import wavelink

def colon_time(millis:int) -> str:
    seconds=(millis/1000)%60
    minutes=(millis/(1000*60))%60
    hours=(millis/(1000*60*60))%24
    if hours >= 1:
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    else:
        return "%02d:%02d" % (minutes, seconds)
    
def track_load_bar(track, length=20):
    loaded = '='
    unloaded = '-'
    
    track_started = track.extras.start_at
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
        self.player = player
        
    @discord.ui.button(emoji="⏯️", custom_id="player_toolbar:playpause", style=discord.ButtonStyle.gray, row=0)
    async def toolbar_playpause(self, inter, button):
        await self.player.pause(not self.player.paused)
        await inter.response.send_message(embed=discord.Embed(description="Paused the player." if self.player.paused else "Resumed the player.", color=0xca5cdd))
        
    @discord.ui.button(emoji="⏭️", custom_id="player_toolbar:next", style=discord.ButtonStyle.gray, row=0)
    async def toolbar_next(self, inter, button):
        await self.player.skip(force=True)
        await inter.response.send_message(embed=discord.Embed(description='Skipped the current song.', color=0xca5cdd))
        
    @discord.ui.button(emoji="⏹️", custom_id="player_toolbar:stop", style=discord.ButtonStyle.red, row=0)
    async def toolbar_stop(self, inter, button):
        self.player.queue.clear()
        await self.player.skip(force=True)
        return await inter.response.send_message(embed=discord.Embed(description='Stopped the player', color=0xca5cff))
    
    @discord.ui.button(emoji="🔁", custom_id="player_toolbar:loop", style=discord.ButtonStyle.gray, row=0)
    async def toolbar_loop(self, inter, button):
        mode_map = {
            "Off": wavelink.QueueMode.normal,
            "Song": wavelink.QueueMode.loop,
            "Queue": wavelink.QueueMode.loop_all
        }  # not used???
        
        self.player.queue.mode = wavelink.QueueMode.loop if self.player.queue.mode == wavelink.QueueMode.normal else wavelink.QueueMode.normal
        if self.player.queue.mode == wavelink.QueueMode.normal:
            await inter.response.send_message(embed=discord.Embed(description=f"Player no longer looping song.", color=0xca5cdd))
        else:
            await inter.response.send_message(embed=discord.Embed(description=f"Player now looping current song.", color=0xca5cdd))

    '''
    # Re-enable after getting a new lyrics host
    @discord.ui.button(label="Lyrics", custom_id="player_toolbar:lyrics", style=discord.ButtonStyle.gray, row=1)
    async def toolbar_lyric(self, inter, button):
        lyrics = self.player.current.extras.lyrics
        if not lyrics:
            return await inter.response.send_message(embed=discord.Embed(description="Error fetching lyrics.\nThe song has no lyrics or song is not in the lyrics database.", color=0xff0000))
            
        total_embeds = []
        for lyric_body in lyrics:
            if len(total_embeds) == 0:
                total_embeds.append(discord.Embed(title=str(self.player.current)+" Lyrics", description=f"```\n{lyric_body}\n```"))
            else:
                total_embeds.append(discord.Embed(description=f"```\n{lyric_body}\n```"))
        
        return await inter.response.send_message(embeds=total_embeds, ephemeral=True)

    '''

class MusicEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener(name='on_wavelink_node_ready')
    async def node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"[Music] Wavelink Node connected: {payload.node} | Resumed: {payload.resumed}")
        
    @commands.Cog.listener(name='on_wavelink_inactive_player')
    async def inactive_player(self, player):
        await player.home.send(embed=discord.Embed(description="Disconnecting the player due to inactivity...", color=0x0000ff))
        await player.disconnect()

    @commands.Cog.listener(name="on_wavelink_track_start")
    async def track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player | None = payload.player
        if not player:
            print("EDGE CASE")
            # Handle edge cases...
            return
        
        # Don't count itself
        if len(player.channel.members)-1 == 0:
            await player.home.send(embed=discord.Embed(description='Disconnecting due to empty channel...'))
            await player.disconnect()
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track
        track.extras.start_at = int(time.time())
        original.extras.start_at = int(time.time())
        print(f"[Music] Track started: {track.title} by {track.author} | Encoded: {track.encoded}")

        embed: discord.Embed = discord.Embed(title="Now Playing", color=random.randint(0, 0xffffff))
        embed.description = f"**{track.title}** by **{track.author}**\n{track_load_bar(track)}"
        #embed.set_author(name=track.author, url=track.artist.url, icon_url=track.artist.artwork)

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        if original and original.recommended:
            embed.set_footer(text=f"This track was recommended via {track.source.title()}")

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        await player.home.send(embed=embed, view=PlayerToolbarView(player))

        # Totally f-ed
        '''
        # Fetching lyrics
        rses = aiohttp.ClientSession()
        async with rses.request(method="GET", url=f"https://lyrist.vercel.app/api/{quote(str(player.current))}/{quote(player.current.author)}") as resp:
            if resp.status >= 300:
                original.extras.start_at = None
                track.extras.lyrics = None
            else:
                lresps = await resp.json()
                track.extras.lyrics = text_splitter(lresps['lyrics'], 4000) if lresps != {} else None
                original.extras.lyrics = text_splitter(lresps['lyrics'], 4000) if lresps != {} else None
            await rses.close()
        '''
        


async def setup(bot):
    await bot.add_cog(MusicEvents(bot))