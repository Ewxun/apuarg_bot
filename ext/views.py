import discord

class WarningConfirmationView(discord.ui.View):
    def __init__(self, invoker_id, callback):
        super().__init__(timeout=60)  # Set a timeout for the view
        self.response = None  # To store the user's response
        self.invoker_id = invoker_id

        self.add_item(discord.ui.Button(label="Yes", style=discord.ButtonStyle.green, custom_id="warning:yes"))
        self.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="warning:no"))

        self.children[0].callback = callback
        self.children[1].callback = callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message("You are not authorized to respond to this confirmation.", ephemeral=True)
            return False
        return True