import discord
from discord.ext import commands
from discord import app_commands

import gspread
from datetime import datetime
from zoneinfo import ZoneInfo

from ext import config

def append_verification_fields(name, tp_number, arcade_games, rhythm_games, know_us, dc_username, verifier, auto_verify=True):
    # Authenticate and select sheet
    gc = gspread.service_account(filename="serv_acc.json")
    spreadsheet = gc.open_by_key(config.get_value('verification.sheet_id'))
    worksheet = spreadsheet.get_worksheet(0)

    # Append the verification fields to the Google Sheet
    try:
        worksheet.append_row([name, tp_number, arcade_games, rhythm_games, know_us, dc_username, str(auto_verify), verifier, datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m-%d %H:%M:%S")])
        return "SUCCESS"
    except gspread.exceptions.APIError as e:
        print(f"Error appending to Google Sheet: {e}")
        return "RATE_LIMIT_EXCEEDED"


class VerifyMessageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Set timeout to None for persistent view

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify_button")    
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerificationModal())

class VerifyMemberButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Verify Member", style=discord.ButtonStyle.green, custom_id=f"verify_button:pending")

    async def callback(self, inter: discord.Interaction):
        if any(role.id in config.get_value('verification.verifiers_roles') for role in 
        inter.user.roles):  # Replace with the role IDs that are allowed to verify users
            ori_message = inter.message
            embed = ori_message.embeds[0]

            for field in embed.fields:
                if field.name == "User":
                    user_id = int(field.value.strip("<@!>"))
                    user = inter.guild.get_member(user_id)
                elif field.name == "Real Name":
                    real_name = field.value
                elif field.name == "TP Number":
                    tp_number = field.value.upper()
                elif field.name == "Arcade Games":
                    arcade_games = field.value
                elif field.name == "Rhythm Games":
                    rhythm_games = field.value
                elif field.name == "How did you find us?":
                    know_us = field.value
            
            if user:
                verify_role = inter.guild.get_role(config.get_value('verification.role_id'))  # Role ID that should be assigned to verified users
                await user.add_roles(verify_role)
                await inter.response.send_message(f"{user.mention} has been verified!", ephemeral=True)
                await user.send(embed=discord.Embed(title="Verification Successful", description=f"You have been verified in {inter.guild.name}!\nWelcome to the community and have a great time!", color=0xca5cdd))

                embed.title = "User Verified"
                embed.color = 0x00ff00
                embed.add_field(name="Verified By", value=inter.user.mention, inline=False)
                embed.add_field(name="Verified At", value=discord.utils.format_dt(inter.created_at, "F"), inline=False)
                await ori_message.edit(view=None, embed=embed)  # Disable the button + edit embed

                # Append the verification fields to Google Sheets
                result = append_verification_fields(real_name, tp_number, arcade_games, rhythm_games, know_us, str(user), str(inter.user))
                if result == "SUCCESS":
                    print(f"Verification data for {user} appended to Google Sheets successfully.")
                elif result == "RATE_LIMIT_EXCEEDED":
                    await inter.followup.send("Rate limit exceeded while trying to append data to Google Sheets. You may need to manually add the data.")
                else:
                    await inter.followup.send("An error occurred while trying to append data to Google Sheets.", ephemeral=True)
            else:
                await inter.response.send_message("User not found.", ephemeral=True)
        else:
            await inter.response.send_message("You do not have permission to verify users.", ephemeral=True, delete_after=5)

class VerifyUserView(discord.ui.View):
    def __init__(self,):
        super().__init__(timeout=None)
        self.add_item(VerifyMemberButton())
        

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
        embed = discord.Embed(title="Pending Verification", color=0x008ce3)
        embed.add_field(name="User", value=interaction.user.mention, inline=False)
        embed.add_field(name="Real Name", value=self.name.component.value, inline=False)
        embed.add_field(name="TP Number", value=self.tp_number.component.value, inline=True)
        embed.add_field(name="Arcade Games", value=self.arcade_games.component.value, inline=False)
        embed.add_field(name="Rhythm Games", value=self.rhythm_games.component.value, inline=False)
        embed.add_field(name="How did you find us?", value=self.know_us.component.value, inline=False)
        embed.add_field(name="Submitted At", value=discord.utils.format_dt(interaction.created_at, "F"), inline=False)

        await verify_resp_channel.send(embed=embed, view=VerifyUserView())

        await interaction.response.send_message("Thank you for submitting the form!\nWe will verify your information. The bot will notify on your verification status via DMs (if you have DMs open).", ephemeral=True)

class Verification_Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(VerifyMessageView())
        self.bot.add_view(VerifyUserView())

    verify_group = app_commands.Group(name="verify", description="Verification commands")

    @verify_group.command(name="user", description="Verify a user")
    @app_commands.describe(user="The user to verify")
    @app_commands.checks.has_any_role(*config.get_value('verification.verifiers_roles'))  # Unpack the list of allowed role IDs from the config
    async def verify_user(self, inter: discord.Interaction, user: discord.Member):
        verify_role = inter.guild.get_role(config.get_value('verification.role_id'))
        await user.add_roles(verify_role) 
        await inter.response.send_message(f"{user.mention} has been manually verified!", ephemeral=True)
        # TODO: Append the verification fields to Google Sheets if possible, but since this is a manual verification, we might not have all the necessary information. Consider adding a way to input that data if needed.

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