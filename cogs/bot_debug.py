import discord
from discord.ext import commands
from discord import app_commands

import random

class EditConfigModal(discord.ui.Modal, title="Edit Config"):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None, custom_id=f"edit_config_modal:{random.randint(0, 9999)}")  # Fix Discord not entering default value after cancelling by giving a unique custom_id
        self.bot = bot
        self.remove_line_count = 5  # Number of lines to remove from the top of the config file (sensitive info)
        self.removed_lines = []

        self.config_content = discord.ui.Label(
            text = "Config File (YAML Format)",
            description = "DO NOT change the structure. Only edit values as needed and only if you know what you're doing.",
            component = discord.ui.TextInput(
                custom_id=f"config_content:input_{random.randint(0, 9999)}",  # Fix Discord not entering default value after cancelling by giving a unique custom_id
                style=discord.TextStyle.paragraph,
                default=self.read_config_safe(),
                placeholder="Enter the updated config content here...",
                required=True
            )
        )

        self.add_item(self.config_content)

    def read_config_safe(self):
        with open('config.yml', 'r') as f:
            raw_content = f.read()

        # Remove first 5 lines, bot sensitive information, and return the rest
        lines = raw_content.splitlines()
        self.removed_lines = lines[:self.remove_line_count]
        return "\n".join(lines[self.remove_line_count:])

    async def on_submit(self, interaction: discord.Interaction):
        # Implement the logic to save the edited config
        new_config_content = self.config_content.component.value
        recombine_content = "\n".join(self.removed_lines) + "\n" + new_config_content
        with open('config.yml', 'w') as f:
            f.write(recombine_content)
        await interaction.response.send_message("Config updated successfully!", ephemeral=True)

    
class BotDebug_Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    debug_group = app_commands.Group(name="debug", description="Debug commands")

    def has_debug_permission(interaction: discord.Interaction) -> bool:
        # Check if the user has perms to use debug commands
        debug_users = [686969234428919832]
        return interaction.user.id in debug_users

    @debug_group.command(name="edit_config", description="Edit the bot's config file")
    @app_commands.check(has_debug_permission)
    async def edit_config(self, interaction: discord.Interaction):
        modal = EditConfigModal(self.bot)
        await interaction.response.send_modal(modal)

    @edit_config.error
    async def edit_config_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

    @app_commands.command(name="purge", description="Delete a specified number of messages from the current channel (Owner only)")
    @app_commands.check(has_debug_permission)
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Please specify a positive number of messages to delete.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeout
        await interaction.channel.purge(limit=amount)  
        await interaction.followup.send(f"Successfully deleted {amount} messages.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(BotDebug_Cog(bot))