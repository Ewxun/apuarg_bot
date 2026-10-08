from typing import cast, Literal
import time
import asyncio

import discord
from discord.ext import commands
from discord import app_commands

import aiohttp
import wavelink

from .music_debug import MusicDebug
from .music_effects import MusicEffectsv2


RELATIVE_VOLUME = 70
LOCK_USER_DEFAULT = None  # Set to None to allow public control of the player by default, or set to True to lock the player to inter.user by default.

async def is_url_on(url, retries=3):
    timeout = aiohttp.ClientTimeout(total=5)  # Set a total timeout of 5 seconds for the request
    for _ in range(retries):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    print(f"URL: {url} | Status: {resp.status}")
                    return resp.status in [401, 403, 200]
        except aiohttp.ClientError as e:
            print(f"URL: {url} | Error: {e}")
            await asyncio.sleep(1)  # Wait before retrying
        except asyncio.TimeoutError:
            print(f"URL: {url} | Timeout occurred")
            await asyncio.sleep(1)  # Wait before retrying
    return False

def truncate_str(s: str, length: int=70):
    return (s[:length] + '...') if len(s) > length else s

def text_splitter(text, split_length):
    num_of_fields = len(text)//split_length + 1
    splitlist = []
    for i in range(num_of_fields):
        splitlist.append(text[i*split_length:i+1*split_length])
    return splitlist

def track_load_bar(player, track, length=20):
    loaded = '='
    unloaded = '-'

    if player.position == 0 and hasattr(player, 'current_start'):
        # Falback if player.position is not available
        track_started = player.current_start
        track_played = (int(time.time()) - track_started) * 1000  # To milliseconds
    else:
        track_played = player.position

    played_percent = (track_played/track.length) * 100
    
    percent = max(0, min(100, played_percent))
    filled_length = int(length * percent // 100)
    
    bar = loaded * (filled_length - 1) + 'O' + unloaded * (length - filled_length)
    text = colon_time(track_played) + '`{' + bar + '}`' + colon_time(track.length)
    return text

def colon_time(millis:int) -> str:
    seconds=(millis/1000)%60
    minutes=(millis/(1000*60))%60
    hours=(millis/(1000*60*60))%24
    if hours >= 1:
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    else:
        return "%02d:%02d" % (minutes, seconds)

class QueueTrackView(discord.ui.View):
    def __init__(self, player, track):
        super().__init__(timeout=None)
        self.player = player
        self.track = track

    @discord.ui.button(label="Remove", custom_id="queue_toolbar:remove_song", style=discord.ButtonStyle.red, row=0)
    async def toolbar_remove(self, inter, button):
        self.player.queue.remove(self.track)
        await inter.response.send_message(embed=discord.Embed(description=f'{inter.user.mention}: Removed **{self.track.title}** by {self.track.author} from the queue.', color=0xff2167))
        

class Music(commands.Cog):
    music_group = app_commands.Group(name='music', description='Music commands')
    queue_group = app_commands.Group(name='queue', description='Queue commands', parent=music_group)
    
    def __init__(self, bot):
        self.bot = bot
        self.bot.use_node = None
        self.relative_volume = RELATIVE_VOLUME
        
        self.play_spotify = app_commands.ContextMenu(
            name='Play Spotify Activity Track',
            callback=self.play_spotify_track,
        )
        self.bot.tree.add_command(self.play_spotify)
        
    async def cog_load(self):
        node_list = self.bot.config.get_value('lavalink_nodes')

        if len(node_list) == 0:
            print("[Music] No Lavalink nodes configured. Please check your config.yml file.")
            return

        connected_nodes = []
        for node_info in node_list:
            if await is_url_on(node_info[0]):
                node = wavelink.Node(uri=node_info[0], password=node_info[1], retries=3)
                connected_nodes.append(node)
        self.bot.connectable_nodes = connected_nodes

        # cache_capacity is EXPERIMENTAL. Turn it off by passing None
        self.bot.connected_lava_nodes = await wavelink.Pool.connect(nodes=connected_nodes, client=self.bot, cache_capacity=None)
        
    async def cog_unload(self):
        for node_id in self.bot.connected_lava_nodes:
            await self.bot.connected_lava_nodes[node_id].close(eject=True)

    async def interaction_check(self, inter: discord.Interaction):
        player: wavelink.Player = inter.guild.voice_client
        
        if inter.user.id in self.bot.owner_ids:
            if not player:
                if inter.command.name in ['play', 'connect']:
                    return True
                await inter.response.send_message(embed=discord.Embed(description=f"Bot is not connected", color=0xca5cff))
                return False
            return True
        if inter.command.name == 'now_playing':
            return True
        if inter.command.name == 'play':
            if not player:
                return True
            if hasattr(player, 'control_user'):
                if player.control_user != inter.user.id and player.control_user != None:
                    await inter.response.send_message(embed=discord.Embed(description=f"The player controls are currently locked to <@{player.control_user}>\n<@{player.control_user}> has to run `/music user_lock` to allow public control of the player", color=0xff0000))
                    return False
                elif player.control_user == None:
                    return True
            else:
                await inter.response.send_message("<@686969234428919832>", embed=discord.Embed(description="This is an absurdly rare error message.\nPlease inform Ewxun ASAP\nError Code: `music.music:76-Player set but attrib. 'control_user' missing", color=0xff0000))
                return False
        if inter.command.name in ['connect', 'Play Spotify Activity Track'] and inter.user.voice:
            return True
        
        if not player:
            await inter.response.send_message(embed=discord.Embed(description="Bot is not connected to any voice channel", color=0xff0000), ephemeral=True)
            return False
        else:
            if player.control_user != inter.user.id and player.control_user != None:
                await inter.response.send_message(embed=discord.Embed(description=f"The player controls are currently locked to <@{player.control_user}>\n<@{player.control_user}> has to run `/music lock_controls` to allow public control of the player", color=0xff0000))
                return False
            elif inter.command.name == 'lock_controls':
                if inter.user.id == player.init_user:
                    return True
                else:
                    await inter.response.send_message(embed=discord.Embed(description=f"The player controls can only be transferred by <@{player.init_user}>", color=0xff0000))
                    return False
            elif player.control_user == None:
                return True
        if not inter.user.voice:
            await inter.response.send_message(embed=discord.Embed(description="You are not connected to any voice channel", color=0xff0000), ephemeral=True)
            return False
        return True
    
    
    async def play_spotify_track(self, interaction: discord.Interaction, member: discord.Member):
        #return await inter.response.send_message(embed=discord.Embed(description='Disabled', color=0xff0000))
        if len(member.activities) == 0:
            return await interaction.response.send_message(embed=discord.Embed(description="User is not playing any Spotify track!", color=0xff0000), ephemeral=True)
        
        found = False
        for activity in member.activities:
            print(type(activity))
            if isinstance(activity, discord.Spotify):
                song_title = activity.title
                song_artist = activity.artist
                found = True
                #return await interaction.response.send_message("Found Data", ephemeral=True)
        if not found:
            return await interaction.response.send_message(embed=discord.Embed(description="User is not playing any Spotify track!", color=0xff0000), ephemeral=True)
        
        inter = interaction
        player: wavelink.Player = inter.guild.voice_client
        
        if not player:
            try:
                player = await inter.user.voice.channel.connect(cls=wavelink.Player)
                await player.set_volume(self.relative_volume)
                player.autoplay = wavelink.AutoPlayMode.partial
                player.control_user = inter.user.id if LOCK_USER_DEFAULT else None
                player.init_user = inter.user.id
                player.inactive_timeout = 150
            except AttributeError:
                await inter.response.send_message(embed=discord.Embed(description="Please join a voice channel first before using this command.", color=0xff0000))
                return
            except discord.ClientException:
                await inter.response.send_message(embed=discord.Embed(description="I was unable to join this voice channel. Please try again.", color=0xff0000))
                return
            
        # Lock the player to this channel...
        if not hasattr(player, "home"):
            player.home = inter.channel
        else:
            if player.home != inter.channel:
                player.home = inter.channel

        tracks: wavelink.Search = await wavelink.Playable.search(f'{song_artist} - {song_title}')
        if not tracks:
            await inter.response.send_message(embed=discord.Embed(description=f"{inter.user.mention} - Could not find any tracks with that query. Please try again.", color=0xff0000))
            return

        if isinstance(tracks, wavelink.Playlist):
            # tracks is a playlist...
            added: int = await player.queue.put_wait(tracks)
            await inter.response.send_message(embed=discord.Embed(description=f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.", color=0xca5cdd))
        else:
            track: wavelink.Playable = tracks[0]
            await player.queue.put_wait(track)
            await inter.response.send_message(embed=discord.Embed(description=f"Added **`{track}`** to the queue.", color=0xca5cdd))

        if not player.playing:
            # Play now since we aren't playing anything...
            await player.play(player.queue.get(), volume=player.volume)
            


    @music_group.command(name="connect")
    @app_commands.describe(channel="Provide a channel to connect.")
    async def connect_channel(self, inter, channel: discord.VoiceChannel=None):
        "Connect to a voice channel."
        if not channel:
            try:
                channel = inter.user.voice.channel
            except:
                return await inter.response.send_message(embed=discord.Embed(description='You are not in a voice channel.', color=0xff0000))

        await inter.response.send_message(embed=discord.Embed(description=f"Connecting to {channel.mention}...", color=0xca5cdd))

        try:
            # Attempt to solve bot instantly disconnecting from VC causing timeout
            # Reloading the cog will fix this, so reconnecting to the Node might fix it?
            try:  
                player = await inter.user.voice.channel.connect(timeout=10, cls=wavelink.Player)
            except wavelink.exceptions.ChannelTimeoutException:
                await inter.edit_original_response(embed=discord.Embed(description="Music server is sleeping... Attempting to wake it up...", color=0x00ffff))
            
                for node_id in self.bot.connected_lava_nodes:
                    await self.bot.connected_lava_nodes[node_id].close(eject=True)
                
                self.bot.connected_lava_nodes = await wavelink.Pool.connect(nodes=self.bot.connectable_nodes, client=self.bot, cache_capacity=None)
                
                # Loops until NodeStatus is connected, then connects to the VC
                first_node: wavelink.Node = list(self.bot.connected_lava_nodes.values())[0] if self.bot.connected_lava_nodes else None
                while first_node.status != wavelink.NodeStatus.CONNECTED:
                    await asyncio.sleep(1)
                    first_node = list(self.bot.connected_lava_nodes.values())[0] if self.bot.connected_lava_nodes else None
                
                player = await inter.user.voice.channel.connect(timeout=10, cls=wavelink.Player)

            await player.set_volume(self.relative_volume)
            player.autoplay = wavelink.AutoPlayMode.partial
            player.init_user = inter.user.id
            player.control_user = inter.user.id if LOCK_USER_DEFAULT else None
            player.inactive_timeout = 150
        except discord.errors.ClientException:
            return await inter.edit_original_response(embed=discord.Embed(description="The bot is already connected to the voice channel.", color=0xff0000))
        
        # Lock the player to this channel...
        if not hasattr(player, "home"):
            player.home = inter.channel
        else:
            if player.home != inter.channel:
                player.home = inter.channel

        await inter.edit_original_response(embed=discord.Embed(description=f'Bot connected to {channel.mention}', color=0xca5cdd))
        
    @music_group.command(name="play")
    @app_commands.describe(query="Provide a query to search for a song. Also accepts URLs. Defaults to YouTube Music.", source="Select the source to search from. Defaults to YouTube Music. Ignore this if you are providing a URL.")
    async def play_cmd(self, inter:discord.Interaction, query: str, source:Literal["YouTube", "YouTubeMusic", "SoundCloud", "Spotify", "Deezer"]='YouTubeMusic') -> None:
        """Play a song with the given query."""
        if not inter.guild:
            return
        
        player: wavelink.Player
        player = inter.guild.voice_client
        await inter.response.send_message(embed=discord.Embed(description=f"Searching for track...", color=0xca5cdd))

        if not player:
            try:
                # Attempt to solve bot instantly disconnecting from VC causing timeout
                # Reloading the cog will fix this, so reconnecting to the Node might fix it?
                try:  
                    player = await inter.user.voice.channel.connect(timeout=10, cls=wavelink.Player)
                except wavelink.exceptions.ChannelTimeoutException:
                    await inter.edit_original_response(embed=discord.Embed(description="Music server is sleeping... Attempting to wake it up...", color=0x00ffff))

                    for node_id in self.bot.connected_lava_nodes:
                        await self.bot.connected_lava_nodes[node_id].close(eject=True)

                    self.bot.connected_lava_nodes = await wavelink.Pool.connect(nodes=self.bot.connectable_nodes, client=self.bot, cache_capacity=None)

                    # Waits until NodeStatus is connected, then connects to the VC
                    first_node: wavelink.Node = list(self.bot.connected_lava_nodes.values())[0] if self.bot.connected_lava_nodes else None
                    while first_node.status != wavelink.NodeStatus.CONNECTED:
                        await asyncio.sleep(1)
                        first_node = list(self.bot.connected_lava_nodes.values())[0] if self.bot.connected_lava_nodes else None

                    player = await inter.user.voice.channel.connect(timeout=10, cls=wavelink.Player)

                await player.set_volume(self.relative_volume)
                player.autoplay = wavelink.AutoPlayMode.partial
                player.init_user = inter.user.id
                player.control_user = inter.user.id if LOCK_USER_DEFAULT else None
                player.inactive_timeout = 150
            except AttributeError:
                await inter.edit_original_response(embed=discord.Embed(description="Please join a voice channel first before using this command.", color=0xff0000))
                return
            except discord.ClientException:
                await inter.edit_original_response(embed=discord.Embed(description="I was unable to join this voice channel. Please try again.", color=0xff0000))
                return
            
        # Lock the player to this channel...
        if not hasattr(player, "home"):
            player.home = inter.channel
        else:
            if player.home != inter.channel:
                player.home = inter.channel

        # This will handle fetching Tracks and Playlists...
        # See the doc strings for more information on this method...
        # If spotify is enabled via LavaSrc, this will automatically fetch Spotify tracks if you pass a URL...
        # Defaults to YouTubeMusic for non URL based queries...
        source_map = {
            "YouTube": wavelink.TrackSource.YouTube,
            "YouTubeMusic": wavelink.TrackSource.YouTubeMusic,
            "SoundCloud": wavelink.TrackSource.SoundCloud,

            # Handled by LavaSrc if enabled
            "Spotify": None,  
            "Deezer": None
        }

        if source == "Spotify":
            query = "spsearch:" + query
        elif source == "Deezer":
            query = "dzsearch:" + query

        try:
            tracks: wavelink.Search = await wavelink.Playable.search(query, source=source_map[source], node=self.bot.use_node)
        except wavelink.exceptions.NodeException as e:
            if e.__context__ and "422" in str(e.__context__):
                await inter.edit_original_response(embed=discord.Embed(description=f"{inter.user.mention} - The URL you provided is invalid or restricted.", color=0xff0000))
            elif e.__context__ and "502" in str(e.__context__):
                await inter.edit_original_response(embed=discord.Embed(description=f"{inter.user.mention} - Y-you're going too fast!!! Slow down and try again later.", color=0xff0000))
            else:
                await inter.edit_original_response(embed=discord.Embed(description=f"{inter.user.mention} - An invalid search query/URL was provided.", color=0xff0000))
            return
        except wavelink.exceptions.LavalinkLoadException as e:
            if "https://" in query or "http://" in query:
                await inter.edit_original_response(embed=discord.Embed(description=f"{inter.user.mention} - The URL you provided is restricted or is unavailable.", color=0xff0000))
            else:
                await inter.edit_original_response(embed=discord.Embed(description=f"{inter.user.mention} - An error occurred while searching for the track: {e}", color=0xff0000))
            return
        
        if not tracks:
            await inter.edit_original_response(embed=discord.Embed(description=f"{inter.user.mention} - Could not find any tracks with that query. Please try again.", color=0xff0000))
            return
        
        if isinstance(tracks, wavelink.Playlist):    # tracks is a playlist..
            added: int = await player.queue.put_wait(tracks)
            await inter.edit_original_response(embed=discord.Embed(description=f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.", color=0xca5cdd))
        else:
            track: wavelink.Playable = tracks[0]   # search query returns a list of tracks, so we take the first one
            
            
            add_queue_embed = discord.Embed(description=f"Added **`{track}`** by **{track.author}** to the queue.", color=0xca5cdd)

            if track.artwork:
                add_queue_embed.set_thumbnail(url=track.artwork)

            # Add toolbar buttons to the embed
            add_toolbar = QueueTrackView(player, track)
            # Calculate the estimated time until the track plays
            if player.queue.is_empty and not player.current:
                # The track will play immediately since the queue is empty and nothing is playing
                estimated_time = "Now"
                add_toolbar = None  # No need for toolbar buttons since the track will play immediately
            elif player.queue.is_empty and player.current:
                # The track will play after the current track finishes
                playing_track = player.current

                if player.position == 0 and hasattr(player, 'current_start'):
                    # Falback if player.position is not available
                    track_started = player.current_start
                    track_played = (int(time.time()) - track_started) * 1000  # Convert to milliseconds
                else:
                    track_played = player.position

                remaining_time = colon_time(playing_track.length - track_played)
                estimated_time = f"`{remaining_time}` (Next)"
            else:
                # The track will play after all other tracks in the queue finish
                estimated_time = sum(t.length for t in player.queue)
                playing_track = player.current

                if player.position == 0 and hasattr(player, 'current_start'):
                    # Falback if player.position is not available
                    track_started = player.current_start
                    track_played = (int(time.time()) - track_started) * 1000  # Convert to milliseconds
                else:
                    track_played = player.position

                if playing_track is None:
                    current_remaining_time = 0
                else:
                    current_remaining_time = playing_track.length - track_played
                estimated_time = f"`{colon_time(estimated_time+current_remaining_time)}`"

            await player.queue.put_wait(track)
            add_queue_embed.add_field(name="Duration", value=f"`{colon_time(track.length)}`", inline=True)
            add_queue_embed.add_field(name="Position in queue", value=f"`{player.queue.count}`", inline=True)
            add_queue_embed.add_field(name="Estimated time until play", value=estimated_time, inline=True)

            add_queue_embed.set_footer(text=f"Requested by {inter.user}", icon_url=inter.user.display_avatar.url)

            if add_toolbar:
                await inter.edit_original_response(embed=add_queue_embed, view=add_toolbar)
            else:
                await inter.edit_original_response(embed=add_queue_embed)

        if not player.current:
            # Play now since we aren't playing anything...
            await player.play(player.queue.get(), volume=player.volume)

    @music_group.command(name="lyrics", description="Get the lyrics of the current song")
    async def get_lyrics(self, inter):
        player: wavelink.Player = inter.guild.voice_client
        if not player or not player.current:
            return await inter.response.send_message(embed=discord.Embed(description="Bot is not playing anything", color=0xff0000), ephemeral=True)

        await inter.response.send_message(embed=discord.Embed(description="Fetching lyrics...", color=0xca5cdd))
        node = player.node
        node_info = await node.fetch_info()
        plugins = [pl.name for pl in node_info.plugins]
        if "lavalyrics-plugin" not in plugins:
            return await inter.response.send_message(embed=discord.Embed(description="Lyrics currently disabled", color=0xff0000))

        session_id = node.session_id
        try:
            lyrics_data = await node.send("GET", path=f"v4/sessions/{session_id}/players/{inter.guild.id}/track/lyrics?skipTrackSource=false")
        except wavelink.exceptions.LavalinkException as e:
            return await inter.edit_original_response(embed=discord.Embed(description=f"Error fetching lyrics or no lyrics available.", color=0xff0000))

        if lyrics_data["text"] and len(lyrics_data["text"]) > 2:
            lyrics_text = lyrics_data["text"]
            lyrics_text_splitlines = lyrics_text.splitlines()
        else:
            lyrics_text_splitlines = [line["line"] for line in lyrics_data["lines"]]

        # Split the lyrics into chunks of 4000 characters in respect to the lines, so we don't cut off lines in the middle
        lyrics_chunks = []
        current_chunk = ""
        for line in lyrics_text_splitlines:
            if len(current_chunk) + len(line) + 1 > 4000:
                lyrics_chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += "\n" + line if current_chunk else line

        # Add the last chunk if it has content / Whole lyrics are less than 4000 characters, this will be the only chunk
        if current_chunk:
            lyrics_chunks.append(current_chunk)

        embeds = []
        for chunk in lyrics_chunks:
            embed = discord.Embed(description=f"```\n{chunk}\n```", color=0xca5cdd)
            embeds.append(embed)

        current_track_title = player.current.title 
        current_track_author = player.current.author
        current_track_artwork = player.current.artwork

        # Add the current track info to the first embed
        if embeds:
            embeds[0].title = f"Lyrics for **{current_track_title}** by **{current_track_author}**"
            if current_track_artwork:
                embeds[0].set_thumbnail(url=current_track_artwork)

        await inter.edit_original_response(content=None, embeds=embeds)

    @music_group.command(name='loop', description='Selects the loop mode.')
    async def loop_mode(self, inter, mode:Literal['Off', 'Song', 'Queue']):
        player: wavelink.Player = inter.guild.voice_client
        mode_map = {
            "Off": wavelink.QueueMode.normal,
            "Song": wavelink.QueueMode.loop,
            "Queue": wavelink.QueueMode.loop_all
        }
        
        player.queue.mode = mode_map[mode]
        await inter.response.send_message(embed=discord.Embed(description=f"Set loop mode to `{mode}`", color=0xca5cdd))
 
    @music_group.command(name='auto_play', description='Whether to fetch song recommendations after the queue is exhausted')
    async def autoplay_mode(self, inter, autoplay:Literal['Enable', 'Disable']):
        player: wavelink.Player = inter.guild.voice_client
        autoplay_map = {
            'Enable': wavelink.AutoPlayMode.enabled,
            'Disable': wavelink.AutoPlayMode.partial
        }
        player.autoplay = autoplay_map[autoplay]
        return await inter.response.send_message(embed=discord.Embed(description=f'{autoplay}d auto play.', color=0xca5cff))
    
    @music_group.command(name='stop', description="Clears the queue and stops the player, but doesn't leave the channel")
    async def stop_player(self, inter):
        player: wavelink.Player = inter.guild.voice_client
        
        player.queue.clear()
        await player.skip(force=True)
        return await inter.response.send_message(embed=discord.Embed(description='Stopped the player', color=0xca5cff))

    @music_group.command(name='skip', description="Skip the current song.")
    async def skip(self, inter):
        player: wavelink.Player = inter.guild.voice_client
        await player.skip(force=True)
        await inter.response.send_message(embed=discord.Embed(description='Skipped the current song.', color=0xca5cdd))

    @music_group.command(name="seek")
    @app_commands.describe(seconds="Input the amount of seconds you want to seek")
    async def forward(self, inter, seconds:int=10):
        "Forwards by a certain amount of time in the current track. The default is 10s."
        player: wavelink.Player = inter.guild.voice_client
        
        if not player.current:
            return await inter.response.send_message("Bot is not playing anything", ephemeral=True)

        # Make it look like now_playing has progressed the seeked seconds
        if hasattr(player, 'current_start'):
            player.current_start = player.current_start - seconds
        
        num = seconds*1000
        await player.seek(int(player.position + num))
        await inter.response.send_message(embed=discord.Embed(description=f'Seeked **{seconds}** seconds', color=0xca5cdd))

    @music_group.command(name="rewind")
    @app_commands.describe(seconds="Input an amount you want to rewind")
    async def go_back(self, inter, seconds:int=10):
        "Rewinds by a certain amount of time in the current track. The default is 10s."
        player: wavelink.Player = inter.guild.voice_client

        if not player.current:
            return await inter.response.send_message("Bot is not playing anything", ephemeral=True)

        # Make it look like now_playing has deducted the rewinded seconds
        if hasattr(player, 'current_start'):
            player.current_start = player.current_start + seconds
        
        num = seconds*1000
        await player.seek(int(player.position - num))
        await inter.response.send_message(embed=discord.Embed(description=f'Rewinded {seconds} seconds', color=0xca5cdd))


    @music_group.command(name="pause_resume", description="Pause or resume the current song.")
    async def pauseresume(self, inter):
        player: wavelink.Player = cast(wavelink.Player, inter.guild.voice_client)

        await player.pause(not player.paused)
        await inter.response.send_message(embed=discord.Embed(description="Paused the player." if player.paused else "Resumed the player.", color=0xca5cdd))

    @music_group.command(name="now_playing", description="Shows details of the current track.")
    async def nowplaying(self, inter):
        player: wavelink.Player = inter.guild.voice_client

        if not player.current:
            return await inter.response.send_message("Bot is not playing anything", ephemeral=True)

        embed = discord.Embed(title="Now Playing", description=f"**{player.current.title}** by **{player.current.author}** \n{track_load_bar(player, player.current)}")
        if player.current.artwork:
            embed.set_thumbnail(url=player.current.artwork)

        await inter.response.send_message(embed=embed)

    @music_group.command(name="lock_controls", description='Locks the player controls to you or a user you selected')
    async def lockcont(self, inter, user:discord.Member=None):
        if not user:
            user = inter.user
        player: wavelink.Player = inter.guild.voice_client
        if not hasattr(player, 'control_user'):
            player.control_user = user.id
            return await inter.response.send_message(embed=discord.Embed(description=f"Player controls now set to {user.mention}", color=0xca5cff))
        
        if player.control_user == inter.user.id:
            player.control_user = None
            return await inter.response.send_message(embed=discord.Embed(description="Player controls now set to **public**", color=0xca5cff))
        elif not player.control_user:
            if inter.user.id == player.init_user:
                if user.id != inter.user.id:
                    player.init_user = user.id
                player.control_user = user.id
                return await inter.response.send_message(embed=discord.Embed(description=f"Player controls now set to {user.mention}", color=0xca5cff))
            else:
                return await inter.response.send_message(embed=discord.Embed(description=f"Player controls now set to <@{player.init_user}> can transfer controls", color=0xca5cff))

    @music_group.command()
    async def volume(self, inter, value:app_commands.Range[int, 0, int(100/RELATIVE_VOLUME)*100]):
        """Change the volume of the player."""
        player: wavelink.Player = cast(wavelink.Player, inter.guild.voice_client)
        
        await player.set_volume(int(self.relative_volume*(value/100)))
        await inter.response.send_message(f"Set the volume to **{value}%**")

    @queue_group.command(name='view', description="View the current queue.")
    async def view_queue(self, inter):
        # TODO: Add pagination for queues with more than 15 songs
        player: wavelink.Player = inter.guild.voice_client

        queue = player.queue
        if len(queue) == 0:
            return await inter.response.send_message(embed=discord.Embed(description="The queue is empty.", color=0xff0000))

        embed = discord.Embed(title="Queue", description='\n', color=0xca5cdd)
        for i, song in enumerate(queue, 1):
            if i <= 15:
                embed.description += f"{i}. **{truncate_str(song.title)}** by {song.author}\n"
            else:
                embed.description += f"**_{len(queue)-15} more songs..._**"
                break

        await inter.response.send_message(embed=embed)

    @queue_group.command(name='history', description="View history of played songs.")
    async def song_hist(self, inter):
        player: wavelink.Player = inter.guild.voice_client

        history = player.queue.history
        if len(history) == 0:
            return await inter.response.send_message(embed=discord.Embed(description="The history is empty.", color=0xff0000))

        embed = discord.Embed(title="History", description='\n', color=0xca5cdd)
        for i, song in enumerate(history, 1):
            if i <= 15:
                embed.description += f"{i}. **{truncate_str(song.title)}** by {song.author}\n"
            else:
                embed.description += f"**_{len(history)-15} more songs..._**"
                break

        await inter.response.send_message(embed=embed)

    @queue_group.command(name='remove', description="Remove a song from the queue.")
    async def q_remove(self, inter, pos:int):
        player: wavelink.Player = inter.guild.voice_client

        queue = player.queue
        if len(queue) == 0:
            return await inter.response.send_message(embed=discord.Embed(description="The queue is empty.", color=0xff0000))

        if pos > len(queue):
            return await inter.response.send_message(embed=discord.Embed(description="Invalid position.", color=0xff0000))

        removed_song = queue[pos-1]
        queue.remove(removed_song)
        rem_embed = discord.Embed(description=f"Removed **{removed_song.title}** by {removed_song.author} from the queue. (Position: {pos})", color=0xff2167)
        rem_embed.set_thumbnail(url=removed_song.artwork)
        await inter.response.send_message(embed=rem_embed)

    @queue_group.command(name='swap', description="Change positions of 2 songs in the queue.")
    async def q_swap(self, inter, pos1:int, pos2:int):
        player: wavelink.Player = inter.guild.voice_client

        queue = player.queue
        if len(queue) == 0:
            return await inter.response.send_message(embed=discord.Embed(description="The queue is empty.", color=0xff0000))

        if pos1 > len(queue) or pos2 > len(queue):
            return await inter.response.send_message(embed=discord.Embed(description="Invalid positions.", color=0xff0000))

        queue.swap(pos1-1, pos2-1)
        await inter.response.send_message(embed=discord.Embed(description=f"Swapped positions {pos1} and {pos2}", color=0xca5cdd))

    @queue_group.command(name="clear", description="Clears the queue.")
    async def clear_q(self, inter):
        player: wavelink.Player = inter.guild.voice_client
        
        player.queue.clear()
        await inter.response.send_message(embed=discord.Embed(description="Cleared the queue", color=0xca5cdd))
        
    @queue_group.command(name="shuffle", description="Shuffle the queue.")
    async def shuffle_q(self, inter):
        player: wavelink.Player = inter.guild.voice_client

        player.queue.shuffle()
        await inter.response.send_message(embed=discord.Embed(description="Shuffled the queue", color=0xca5cdd))

    @music_group.command(name='disconnect', description="Disconnects the bot from the voice channel.")
    async def disconnect(self, inter):
        player: wavelink.Player = cast(wavelink.Player, inter.guild.voice_client)
        
        await player.disconnect()
        await inter.response.send_message(embed=discord.Embed(description="Disconnected the player.", color=0xca5cdd))     


async def setup(bot):
    await bot.add_cog(Music(bot))
    mpar = bot.tree.get_command("music")
    mpar.add_command(MusicDebug(bot))
    mpar.add_command(MusicEffectsv2(bot))