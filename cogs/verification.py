import discord
from discord.ext import commands
from discord import app_commands

from ext import config

class VerifyMessageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Set timeout to None for persistent view

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify_button")    
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerificationModal())

class VerifyMemberButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(label="Verify Member", style=discord.ButtonStyle.green, custom_id=f"verify_button:{user_id}")
        self.user_id = user_id

    async def callback(self, inter: discord.Interaction):
        if any(role.id in config.get_value('verification.verifiers_roles') for role in inter.user.roles):  # Replace with the role IDs that are allowed to verify users
            user = inter.guild.get_member(self.user_id)
            if user:
                verify_role = inter.guild.get_role(config.get_value('verification.role_id'))  # Role ID that should be assigned to verified users
                await user.add_roles(verify_role)
                await inter.response.send_message(f"{user.mention} has been verified!", ephemeral=True)
            else:
                await inter.response.send_message("User not found.", ephemeral=True)
        else:
            await inter.response.send_message("You do not have permission to verify users.", ephemeral=True, delete_after=5)

class VerifyUserView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.add_item(VerifyMemberButton(user_id))
        

class VerificationModal(discord.ui.Modal, title="Verification Form"):
    def __init__(self):
        super().__init__(timeout=None, custom_id="verification_modal:1")

    name = discord.ui.Label(
        text = "Real Name", 
        description = "Your name as appears on your APCard",
        component = discord.ui.TextInput(
            style=discord.TextStyle.short,
            placeholder='Eg: Tan Mai Mai',
        ),
    )
    tp_number = discord.ui.Label(
        text = "TP Number",
        component = discord.ui.TextInput(
            style=discord.TextStyle.short,
            placeholder='Eg: TPXXXXXX',
        ),
    )
    arcade_games = discord.ui.Label(
        text = "Arcade Games You Play",
        description = "Rhythm arcade games also count",
        component = discord.ui.TextInput(
            style=discord.TextStyle.short,
            placeholder='Eg: Wangan Midnight, Initial D, Maimai, etc.',
        ),
    )
    rhythm_games = discord.ui.Label(
        text = "Rhythm Games You Play",
        component = discord.ui.TextInput(
            style=discord.TextStyle.short,
            placeholder='Eg: Muse Dash, Osu!, Arcaea, etc.',
        ),
    )
    know_us = discord.ui.Label(
        text = "How did you find out about us?",
        component = discord.ui.TextInput(
            style=discord.TextStyle.short,
            placeholder='Eg: Friend, Social Media, etc.',
        ),
    )


    async def on_submit(self, interaction: discord.Interaction):
        verify_resp_channel = interaction.guild.get_channel(config.get_value('verification.submission_channel_id'))  # Channel ID where the verification responses should be sent
        embed = discord.Embed(title="Verification Submission", color=0x00ff00)
        embed.add_field(name="User", value=interaction.user.mention, inline=False)
        embed.add_field(name="Real Name", value=self.name.component.value, inline=False)
        embed.add_field(name="TP Number", value=self.tp_number.component.value, inline=True)
        embed.add_field(name="Arcade Games", value=self.arcade_games.component.value, inline=False)
        embed.add_field(name="Rhythm Games", value=self.rhythm_games.component.value, inline=False)
        embed.add_field(name="How did you find us?", value=self.know_us.component.value, inline=False)
        embed.add_field(name="Submitted At", value=discord.utils.format_dt(interaction.created_at, "F"), inline=False)

        await verify_resp_channel.send(embed=embed, view=VerifyUserView(interaction.user.id))

        await interaction.response.send_message("Thank you for submitting the form!\nWe will verify your information. The bot will notify on your verification status via DMs (if you have DMs open).", ephemeral=True)

class Verification_Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(VerifyMessageView())  # Add the view with a dummy user ID to keep it persistent

    verify_group = app_commands.Group(name="verify", description="Verification commands")

    @verify_group.command(name="user", description="Verify a user")
    @app_commands.describe(user="The user to verify")
    @app_commands.checks.has_any_role(*config.get_value('verification.verifiers_roles'))  # Unpack the list of allowed role IDs from the config
    async def verify_user(self, inter: discord.Interaction, user: discord.Member):
        verify_role = inter.guild.get_role(config.get_value('verification.role_id'))
        await user.add_roles(verify_role) 
        await inter.response.send_message(f"{user.mention} has been verified!", ephemeral=True)

    @verify_user.error
    async def verify_user_error(self, inter: discord.Interaction, error):
        if isinstance(error, app_commands.MissingAnyRole):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
        else:
            await inter.response.send_message("An error occurred", ephemeral=True)

    @verify_group.command(name="message", description="Send the verification message")
    @app_commands.checks.has_any_role(*config.get_value('verification.verifiers_roles'))  # Unpack the list of allowed role IDs from the config
    async def send_verification_message(self, inter: discord.Interaction):
        embed = discord.Embed(title="Verification", description="Click the button below to verify yourself!", color=0x00ff00)
        embed.set_footer(text="By verifying, you agree to the server rules and guidelines.")
        verify_msg_view = VerifyMessageView()

        await inter.channel.send(embed=embed, view=verify_msg_view)
        await inter.response.send_message("Verification message sent!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Verification_Cog(bot))