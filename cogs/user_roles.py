import discord
from discord.ext import commands
from discord import app_commands

import json

class Rhythm_Roles_Dropdown(discord.ui.Select):
    def __init__(self):
        with open("store/roles/game_ids.json", "r") as f:
            game_ids = json.load(f)

        options = [
            discord.SelectOption(label="Project Sekai", description="W---Wonderhoy!!!", value=str(game_ids["rhythm"]["pjsk"])),
            discord.SelectOption(label="Hololive Dreams", description="Are you sure its not a yuri game?", value=str(game_ids["rhythm"]["holodori"])),
            discord.SelectOption(label="Phigros", description="AT does not mean anti-thumb, absolutely...", value=str(game_ids["rhythm"]["phigros"])),
            discord.SelectOption(label="*K Mania", description="4K, 5K, 6K, even 1K and more", value=str(game_ids["rhythm"]["xk_mania"])),
            discord.SelectOption(label="Arcaea", description="In that light, I find that my assigment is due yesterday", value=str(game_ids["rhythm"]["arcaea"])),
            discord.SelectOption(label="InFalsus", description="Totally not ONGEKI+SVDX on PC", value=str(game_ids["rhythm"]["infalsus"])),
            discord.SelectOption(label="Cytus I/II", description="Judgement line go brrrrrr", value=str(game_ids["rhythm"]["cytus"])),
            discord.SelectOption(label="Muse Dash", description="The main characters looks suspiciously like the triple baka...", value=str(game_ids["rhythm"]["muse_dash"])),
            discord.SelectOption(label="vivid/stasis", description="I'm sure as hell not! - Saturday", value=str(game_ids["rhythm"]["vivid_stasis"])),
            discord.SelectOption(label="Rhythm Doctor", description="rea- dy- get- set", value=str(game_ids["rhythm"]["rhythm_doctor"])),
            discord.SelectOption(label="ADOFAI", description="You know something happened when you need 16+ keys for a \"one key\" rhythm game...", value=str(game_ids["rhythm"]["adofai"])),
            discord.SelectOption(label="DJ Max", description="Why game so expensive? :(", value=str(game_ids["rhythm"]["djmax"])),
            discord.SelectOption(label="Osu!", description="Who's afraid of the big black?", value=str(game_ids["rhythm"]["osu"])),
            discord.SelectOption(label="Geometry Dash", description="FOCUS!", value=str(game_ids["rhythm"]["geometry_dash"])),
        ]
        super().__init__(placeholder="Choose your roles...", min_values=0, max_values=len(options), options=options, custom_id="roles_dropdown:rhythm")

    async def callback(self, interaction: discord.Interaction):
        selected_roles = self.values
        member = interaction.user
        full_list_of_roles = [option.value for option in self.options if option.value]  # Get all role IDs from the options

        added_role_names = []
        removed_role_names = []

        # Remove roles that are not selected
        for role_id in full_list_of_roles:
            role = interaction.guild.get_role(int(role_id))
            if role and role in member.roles and role_id not in selected_roles:
                await member.remove_roles(role)
                removed_role_names.append(role.name)

        # Add selected roles
        for role_id in selected_roles:
            role = interaction.guild.get_role(int(role_id))
            if role and role not in member.roles:
                await member.add_roles(role)
                added_role_names.append(role.name)

        await interaction.response.send_message(f"Roles updated:\n Added: {', '.join(added_role_names)}\n Removed: {', '.join(removed_role_names)}", ephemeral=True)

class Arcade_Roles_Dropdown(discord.ui.Select):
    def __init__(self):
        with open("store/roles/game_ids.json", "r") as f:
            game_ids = json.load(f)

        options = [
            discord.SelectOption(label="Pump It Up", description="Its like dancing but I really hate myself", value=str(game_ids["arcade"]["pump_it_up"])),
            discord.SelectOption(label="Maimai", description="oooo look, washing machine game", value=str(game_ids["arcade"]["maimai"])),
            discord.SelectOption(label="Chunithm", description="oooo look, Project Sekai in an arcade machine", value=str(game_ids["arcade"]["chunithm"])),
            discord.SelectOption(label="ONGEKI", description="Doesn't really exist in Malaysia, unless...", value=str(game_ids["arcade"]["ongeki"])),
            discord.SelectOption(label="Sound Voltex", description="Turning the knobs reminds me of something...", value=str(game_ids["arcade"]["sound_voltex"])),
            discord.SelectOption(label="Taiko no Tatsujin", description="Its like playing the drums but I really hate myself", value=str(game_ids["arcade"]["taiko_no_tatsujin"])),
            discord.SelectOption(label="Pop'n Music", description="Looks like a kids game but its not?", value=str(game_ids["arcade"]["popnmusic"])),
            discord.SelectOption(label="Initial D", description="Deja vu, I've just been in this place before...", value=str(game_ids["arcade"]["initial_d"])),
            discord.SelectOption(label="Wangan Midnight", description="Kissing the C1 loop bridge divider", value=str(game_ids["arcade"]["wmmt"])),
            discord.SelectOption(label="Tetris", description="Barely anyone knows the actual name of the theme", value=str(game_ids["arcade"]["tetris"])),
        ]
        super().__init__(placeholder="Choose your roles...", min_values=0, max_values=len(options), options=options, custom_id="roles_dropdown:arcade")

    async def callback(self, interaction: discord.Interaction):
        selected_roles = self.values
        member = interaction.user
        added_role_names = []
        removed_role_names = []

        full_list_of_roles = [option.value for option in self.options if option.value]
        for role_id in full_list_of_roles:
            role = interaction.guild.get_role(int(role_id))
            if role and role in member.roles and role_id not in selected_roles:
                await member.remove_roles(role)
                removed_role_names.append(role.name)

        for role_id in selected_roles:
            role = interaction.guild.get_role(int(role_id))
            if role and role not in member.roles:
                await member.add_roles(role)
                added_role_names.append(role.name)

        await interaction.response.send_message(f"Roles updated:\n Added: {', '.join(added_role_names)}\n Removed: {', '.join(removed_role_names)}", ephemeral=True)

class Roles_View(discord.ui.View):
    def __init__(self, dropdown: discord.ui.Select):
        super().__init__(timeout=None)
        self.add_item(dropdown)

class UserRoles_Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    user_roles_group = app_commands.Group(name="user_roles", description="User role management commands")

    async def cog_load(self):
        # Persistent view setup for the roles dropdowns
        self.bot.add_view(Roles_View(Rhythm_Roles_Dropdown()))
        self.bot.add_view(Roles_View(Arcade_Roles_Dropdown()))

    @user_roles_group.command(name="message", description="Sends a message with buttons for users to assign themselves roles")
    async def send_role_message(self, inter: discord.Interaction):
        head_embed = discord.Embed(title="Assign Yourself Some Roles", description="Select roles from the dropdowns below", color=0x00FF00)

        rhythm_img_file = discord.File("assets/arcaea_pressure.gif", filename="rhythm_roles.gif")
        rhythm_embed = discord.Embed(title="Rhythm Game Roles", color=0x00FF00)
        rhythm_embed.set_image(url="attachment://rhythm_roles.gif")

        arcade_img_file = discord.File("assets/chuni_real.gif", filename="arcade_roles.gif")
        arcade_embed = discord.Embed(title="Arcade Game Roles", color=0x00FF00)
        arcade_embed.set_image(url="attachment://arcade_roles.gif")

        rhythm_view = Roles_View(Rhythm_Roles_Dropdown())
        arcade_view = Roles_View(Arcade_Roles_Dropdown())
        await inter.channel.send(embed=head_embed)
        await inter.channel.send(embed=rhythm_embed, view=rhythm_view, file=rhythm_img_file)
        await inter.channel.send(embed=arcade_embed, view=arcade_view, file=arcade_img_file)

        await inter.response.send_message("Role message sent!", ephemeral=True)

    @user_roles_group.command(name="test", description="Test the role assignment dropdowns")
    async def test_role_dropdowns(self, inter: discord.Interaction):
        await inter.response.send_message("Testing role dropdowns...", ephemeral=True)
        await inter.channel.send(embed=discord.Embed(title="Rhythm Game Roles", color=0x00FF00), view=Roles_View(Rhythm_Roles_Dropdown()))
        await inter.channel.send(embed=discord.Embed(title="Arcade Game Roles", color=0x00FF00), view=Roles_View(Arcade_Roles_Dropdown()))

async def setup(bot: commands.Bot):
    await bot.add_cog(UserRoles_Cog(bot))