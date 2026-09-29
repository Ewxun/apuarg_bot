import discord
from discord.ext import commands
from discord import app_commands

import wavelink

def fmt_time(millis:int) -> str:
    millis = int(millis)
    seconds=(millis/1000)%60
    minutes=(millis/(1000*60))%60
    hours=(millis/(1000*60*60))%24
    if hours >= 1:
        return "%02d hours, %02d minutes, %02d seconds" % (hours, minutes, seconds)
    else:
        return "%02d minutes, %02d seconds" % (minutes, seconds)
    
def byte_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"

class MusicDebug(app_commands.Group):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(name='debug', description='Music Debugging Stuffs')
        
    async def interaction_check(self, inter):
        if inter.user.id in self.bot.owner_ids:
            return True
        else:
            await inter.response.send_message(embed=discord.Embed(description="You don't have permissions to debug.", color=0xff0000))
            return False
        
    @app_commands.command(name="inspect_node", description="Inspects the Lava node from URI")
    async def insp_node(self, inter, uri:str, pw:str):
        lv_node = wavelink.Node(uri=uri, password=pw)
        await lv_node._connect(client=self.bot)
        embed = discord.Embed(title="Inspect Node", color=0xca5cff)
        if True:
            node = lv_node
            node_stat = await node.fetch_stats()
            node_info = await node.fetch_info()
            
            plugin_fmt = [f"`{pl.name} (v{pl.version})`" for pl in node_info.plugins]
            info_body = f"Lavalink Version: `{node_info.version.semver}`\nJVM Version: `{node_info.jvm}`\nLavaplayer Version: `{node_info.lavaplayer}`\nSource Managers: `{', '.join(node_info.source_managers)}`\nPlugins: {', '.join(plugin_fmt)}\n\n"
            info_body += f"Connected Players: `{node_stat.players}`\nActive Players: `{node_stat.playing}`\nNode Uptime: `{fmt_time(node_stat.uptime)}`\nCPU: `{round(node_stat.cpu.system_load*100, 2)} % /{node_stat.cpu.cores}00 %` (`{round(node_stat.cpu.lavalink_load*100, 2)} % by Lavalink`)\nMemory: `{byte_fmt(node_stat.memory.used)} / {byte_fmt(node_stat.memory.allocated)}`"
            if node_stat.frames:
                info_body += f"\n**__Frames__**\n- Sent: `{node_stat.frames.sent}`\n- Nulled: `{node_stat.frames.nulled}`\n- Deficit: `{node_stat.frames.deficit}`"
            
            embed.add_field(name=node.uri.split(":",1)[1].replace("/",""), value=info_body)
            
        await lv_node.close()
        await inter.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="list_nodes", description="List all connected nodes and their status")
    async def list_lave_nodes(self, inter):
        lava_nodes = self.bot.connected_lava_nodes
        embed = discord.Embed(title="Connected Nodes", color=0xca5cff)
        for node_id in lava_nodes:
            node = lava_nodes[node_id]
            node_stat = await node.fetch_stats()
            node_info = await node.fetch_info()
            
            plugin_fmt = [f"`{pl.name} (v{pl.version})`" for pl in node_info.plugins]
            info_body = f"Lavalink Version: `{node_info.version.semver}`\nJVM Version: `{node_info.jvm}`\nLavaplayer Version: `{node_info.lavaplayer}`\nSource Managers: `{', '.join(node_info.source_managers)}`\nPlugins: {', '.join(plugin_fmt)}\n\n"
            info_body += f"Connected Players: `{node_stat.players}`\nActive Players: `{node_stat.playing}`\nNode Uptime: `{fmt_time(node_stat.uptime)}`\nCPU: `{round(node_stat.cpu.system_load*100, 2)} % /{node_stat.cpu.cores}00 %` (`{round(node_stat.cpu.lavalink_load*100, 2)} % by Lavalink`)\nMemory: `{byte_fmt(node_stat.memory.used)} / {byte_fmt(node_stat.memory.allocated)}`"
            if node_stat.frames:
                info_body += f"\n**__Frames__**\n- Sent: `{node_stat.frames.sent}`\n- Nulled: `{node_stat.frames.nulled}`\n- Deficit: `{node_stat.frames.deficit}`"
            
            embed.add_field(name=node.uri.split(":",1)[1].replace("/",""), value=info_body)
            
        await inter.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="player_info", description="Views the guild's player info")
    async def view_player_stat(self, inter):
        lava_nodes = self.bot.connected_lava_nodes
        embed = discord.Embed(title="Guild Players", color=0xca5cff)
        use_node = None
        
        for node_id in lava_nodes:
            node = lava_nodes[node_id]
            player_stat = await node.fetch_player_info(inter.guild.id)
            if player_stat:
                # Specifies which node the player is using
                use_node = node
                break
        if use_node:
            embed.description = f'Worker Node: `{use_node.uri.split(":",1)[1].replace("/","")}`'
            embed.add_field(name="Track", value=str(player_stat.track))
            embed.add_field(name="Absolute Volume", value=str(player_stat.volume))
            embed.add_field(name="Paused", value=str(player_stat.paused))
            embed.add_field(name="Voice Client Endpoint", value=str(player_stat.voice_state.endpoint))
            
            ps_body = f"- Time: `{player_stat.state.time}`\n- Position: `{player_stat.state.position}`\n- Connected: `{player_stat.state.connected}`\n- Ping: `{player_stat.state.ping} ms`"
            embed.add_field(name="Player State", value=ps_body)
            return await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            return await inter.response.send_message(embed=discord.Embed(description="There are no players in this guild!", color=0xff0000), ephemeral=True)
        

async def setup(bot):
    return