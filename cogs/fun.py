import discord
from discord.ext import commands
from discord import app_commands

import json
import yt_dlp
import os
import random

from ext.views import WarningConfirmationView


def get_song_thumbnail(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'forcejson': True,
        'extract_flat': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get('thumbnail', None)


class CreateSongListDescriptionModal(discord.ui.Modal, title="Create a Song List"):
    def __init__(self, curator: discord.Member):
        super().__init__(timeout=None, custom_id=f"song_list_desc:{curator.id}")
        self.curator = curator

        self.add_item(discord.ui.Label(
            text = "Song List Description (Optional)",
            description = "Displayed when someone requests a random song from your list. Max length: 3000 characters.",
            component = discord.ui.TextInput(style=discord.TextStyle.paragraph, placeholder="Enter a description for your song list...", required=False, max_length=3000)
        ))

    def create_song_list(self, curator, description=""):
        song_recs_file = f"store/song_recs/{curator.id}.json"
        new_song_list = {
            "description": description,
            "songs": []
        }
        with open(song_recs_file, "w") as f:
            json.dump(new_song_list, f, indent=4)

    async def on_submit(self, interaction: discord.Interaction):
        description = self.children[0].component.value
        await interaction.response.send_message(f"Creating your song list...", ephemeral=True)
        self.create_song_list(self.curator, description)
        embed = discord.Embed(description=f"Your song list has been created! Use `/song_list edit` to add songs to your list.", color=0x00FF00)
        await interaction.followup.send(embed=embed, ephemeral=True)

class EditSongModal(discord.ui.Modal, title="Edit Song Info"):
    def __init__(self, curator: discord.Member, song_index: int):
        super().__init__(timeout=None, custom_id=f"edit_song:{curator.id}:{song_index}")
        self.curator = curator
        self.song_index = song_index

        with open(f"store/song_recs/{curator.id}.json", "r") as f:
            song_recs = json.load(f)
            song = song_recs["songs"][song_index]

        song_name = song.get("name", "")
        artist_name = song.get("artist", "")
        song_link = song.get("link", "")
        notes = song.get("notes") if song.get("notes") != "" else None

        self.add_item(discord.ui.Label(
            text = "Song Name",
            component = discord.ui.TextInput(style=discord.TextStyle.short, placeholder="Enter the song name...", required=True, default=song_name)
        ))

        self.add_item(discord.ui.Label(
            text = "Artist Name",
            component = discord.ui.TextInput(style=discord.TextStyle.short, placeholder="Enter the artist name...", required=True, default=artist_name)
        ))

        self.add_item(discord.ui.Label(
            text = "Song Link",
            description = "A link to the song (e.g., YouTube, Spotify)",
            component = discord.ui.TextInput(style=discord.TextStyle.short, placeholder="Enter a link to the song...", required=True, default=song_link)
        ))

        self.add_item(discord.ui.Label(
            text = "Notes About this Song (Optional)",
            description = "Any additional notes about this song. Max length: 512 characters.",
            component = discord.ui.TextInput(style=discord.TextStyle.paragraph, placeholder="Enter any notes about this song...", required=False, max_length=512, default=notes)
        ))

    async def on_submit(self, interaction: discord.Interaction):
        song_name = self.children[0].component.value
        artist_name = self.children[1].component.value
        song_link = self.children[2].component.value
        notes = self.children[3].component.value

        with open(f"store/song_recs/{self.curator.id}.json", "r") as f:
            song_recs = json.load(f)

        song_recs["songs"][self.song_index] = {
            "name": song_name,
            "artist": artist_name,
            "link": song_link,
            "notes": notes
        }

        with open(f"store/song_recs/{self.curator.id}.json", "w") as f:
            json.dump(song_recs, f, indent=4)

        embed = discord.Embed(description=f"Song #{self.song_index + 1} updated successfully!", color=0x00FF00)
        embed.set_footer(text=f"The update will be reflected next time you view your song list")
        await interaction.response.send_message(embed=embed, ephemeral=True)

def song_list_paginator(curator, page=0):
    song_recs_file = f"store/song_recs/{curator.id}.json"

    if not os.path.exists(song_recs_file):
        return None

    with open(song_recs_file, "r") as f:
        song_recs = json.load(f)

    songs_per_page = 10
    total_pages = (len(song_recs["songs"]) + songs_per_page - 1) // songs_per_page
    page = max(0, min(page, total_pages - 1))  # Ensure the page is within bounds

    start_index = page * songs_per_page
    end_index = start_index + songs_per_page
    current_songs = song_recs["songs"][start_index:end_index]

    embed = discord.Embed(title=f"{curator.display_name}'s Song List", color=0x00FF00)
    if song_recs["description"] and song_recs["description"].strip() != "":
        embed.description = f"Curator's Description: {song_recs['description']}\n\n"

    for idx, song in enumerate(current_songs, start=start_index + 1):
        embed.description += f"**{idx}. {song['name']}**\nArtist: {song['artist']}\nLink: {song['link']}\n\n"

    embed.set_footer(text=f"Page {page + 1} of {total_pages}")

    return embed

def song_list_option_paginator(curator, page=0):
    song_recs_file = f"store/song_recs/{curator.id}.json"

    if not os.path.exists(song_recs_file):
        return None

    with open(song_recs_file, "r") as f:
        song_recs = json.load(f)

    songs_per_page = 10
    total_pages = (len(song_recs["songs"]) + songs_per_page - 1) // songs_per_page
    page = max(0, min(page, total_pages - 1))  # Ensure the page is within bounds

    start_index = page * songs_per_page
    end_index = start_index + songs_per_page
    current_songs = song_recs["songs"][start_index:end_index]

    # Slice the song name and artist if > 95 characters and add "..." to the end
    for song in current_songs:
        if len(song['name']) > 95:
            song['name'] = song['name'][:92] + "..."
        if len(song['artist']) > 95:
            song['artist'] = song['artist'][:92] + "..."

    options = [
        discord.SelectOption(label=f"{idx + 1}. {song['name']}", description=song['artist'], value=str(idx))
        for idx, song in enumerate(current_songs, start=start_index)
    ]

    return options

class ViewSongListPaginatorView(discord.ui.View):
    def __init__(self, curator: discord.Member, page=0):
        super().__init__(timeout=None)
        self.curator = curator
        self.page = page

        # Add navigation buttons
        self.add_item(discord.ui.Button(label="Previous Page", style=discord.ButtonStyle.blurple, custom_id="song_list:prev"))
        self.add_item(discord.ui.Button(label="Next Page", style=discord.ButtonStyle.blurple, custom_id="song_list:next"))

        self.children[0].callback = self.button_callback
        self.children[1].callback = self.button_callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.curator.id:
            await interaction.response.send_message("You are not authorized to navigate this song list.", ephemeral=True)
            return False
        return True

    async def button_callback(self, interaction: discord.Interaction):
        if interaction.custom_id == "song_list:prev":
            self.page -= 1
        elif interaction.custom_id == "song_list:next":
            self.page += 1

        embed = song_list_paginator(self.curator, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

class SongListSelect(discord.ui.Select):
    def __init__(self, curator: discord.Member, row: int, page=0):
        options = song_list_option_paginator(curator, page)
        super().__init__(placeholder="Select a song to edit", options=options, custom_id=f"song_list:{curator.id}:edit_select", row=row)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.custom_id.split(":")[1]):
            await interaction.response.send_message("You are not authorized to edit this song list.", ephemeral=True)
            return

        selected_index = int(self.values[0])
        await interaction.response.send_modal(EditSongModal(interaction.user, selected_index))

class AddSongButton(discord.ui.Button):
    def __init__(self, curator: discord.Member, row: int):
        super().__init__(label="Add Song", style=discord.ButtonStyle.green, custom_id=f"song_list:{curator.id}:add_song", row=row)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.custom_id.split(":")[1]):
            await interaction.response.send_message("You are not authorized to add songs to this list.", ephemeral=True)
            return

        #await interaction.response.send_modal(AddSongModal(interaction.user))

class EditSongButton(discord.ui.Button):
    def __init__(self, curator: discord.Member, row: int):
        super().__init__(label="Edit Song", style=discord.ButtonStyle.blurple, custom_id=f"song_list:{curator.id}:edit_song", row=row)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.custom_id.split(":")[1]):
            await interaction.response.send_message("You are not authorized to edit songs in this list.", ephemeral=True)
            return

        class EditSongSelectView(discord.ui.View):
            def __init__(self, curator: discord.Member, page=0):
                super().__init__(timeout=None)
                self.curator = curator
                self.page = page

                self.add_item(SongListSelect(self.curator, row=0, page=self.page))
                self.add_item(discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="song_list:cancel_edit", row=1))

                self.children[1].callback = self.cancel_edit_callback

            async def cancel_edit_callback(self, interaction: discord.Interaction):
                if interaction.user.id != int(self.custom_id.split(":")[1]):
                    await interaction.response.send_message("You are not authorized to cancel this action.", ephemeral=True)
                    return

                await interaction.response.edit_message(view=EditSongListPaginatorView(interaction.user, self.page))
        
    
        
        await interaction.response.edit_message(view=EditSongSelectView(interaction.user))

class RemoveSongButton(discord.ui.Button):
    def __init__(self, curator: discord.Member, row: int):
        super().__init__(label="Remove Song", style=discord.ButtonStyle.red, custom_id=f"song_list:{curator.id}:remove_song", row=row)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.custom_id.split(":")[1]):
            await interaction.response.send_message("You are not authorized to remove songs from this list.", ephemeral=True)
            return

        #await interaction.response.send_modal(RemoveSongModal(interaction.user))

class EditSongListPaginatorView(discord.ui.View):
    def __init__(self, curator: discord.Member, page=0):
        super().__init__(timeout=300)
        self.curator = curator
        self.page = page

        # Add navigation buttons
        self.add_item(discord.ui.Button(label="Previous Page", style=discord.ButtonStyle.gray, custom_id="song_list:prev", row=0))
        self.add_item(discord.ui.Button(label="Next Page", style=discord.ButtonStyle.gray, custom_id="song_list:next", row=0))

        self.children[0].callback = self.paginator_callback
        self.children[1].callback = self.paginator_callback

        self.add_item(AddSongButton(self.curator, row=1))
        self.add_item(EditSongButton(self.curator, row=1))
        self.add_item(RemoveSongButton(self.curator, row=1))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.curator.id:
            await interaction.response.send_message("You are not authorized to navigate this song list.", ephemeral=True)
            return False
        return True

    async def paginator_callback(self, interaction: discord.Interaction):
        if interaction.custom_id == "song_list:prev":
            self.page -= 1
        elif interaction.custom_id == "song_list:next":
            self.page += 1

        embed = song_list_paginator(self.curator, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

        
    async def remove_song_callback(self, interaction: discord.Interaction):
        # Logic to handle removing a song (e.g., show a modal to select and confirm removal)
        pass

    async def cancel_edit_callback(self, interaction: discord.Interaction):
        for item in self.children:
            if isinstance(item, discord.ui.Select) or (isinstance(item, discord.ui.Button) and item.custom_id == "song_list:cancel_edit"):
                self.remove_item(item)

        self.add_item(discord.ui.Button(label="Add Song", style=discord.ButtonStyle.green, custom_id="song_list:add", row=1))
        self.add_item(discord.ui.Button(label="Edit Song", style=discord.ButtonStyle.blurple, custom_id="song_list:edit", row=1))
        self.add_item(discord.ui.Button(label="Remove Song", style=discord.ButtonStyle.red, custom_id="song_list:remove", row=1))

        await interaction.response.edit_message(view=self)

class Fun_Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    rand_song_group = app_commands.Group(name="song_list", description="Do something with a a list of songs")

    @rand_song_group.command(name="get_random", description="Get a random song from a user's curated song list")
    async def random_song(self, interaction: discord.Interaction, curated_by:discord.Member=None):
        if not curated_by:
            # Change to randomly select a curator from the song recommendations folder later
            curated_by = interaction.guild.get_member(686969234428919832)
        
        song_recs_file = f"store/song_recs/{curated_by.id}.json"

        if not os.path.exists(song_recs_file):
            embed = discord.Embed(description=f"{curated_by.mention} has not curated any song lists yet. Find another curator!", color=0xFF0000)
            return await interaction.response.send_message(embed=embed)

        with open(song_recs_file, "r") as f:
            song_recs = json.load(f)
        random_song = random.choice(song_recs)

        embed = discord.Embed(title="Random Song Pick", description=f"Curated by: {curated_by.mention}", color=0x00FF00)

        if song_recs["description"] and song_recs["description"].strip() != "":
            embed.description += f"\n\nCurator's List Description: {song_recs['description']}"

        embed.add_field(name="Song", value=random_song["name"], inline=False)
        embed.add_field(name="Artist", value=random_song["artist"], inline=False)
        embed.add_field(name="Link", value=random_song["link"], inline=False)

        if random_song["notes"] and random_song["notes"].strip() != "":
            embed.add_field(name="Notes About this Song", value=random_song["notes"], inline=False)
        
        song_thumbnail = get_song_thumbnail(random_song["link"])
        if song_thumbnail:
            embed.set_image(url=song_thumbnail)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rand_song_group.command(name="create", description="Create a new song list for yourself")
    async def create_list(self, interaction: discord.Interaction):
        song_recs_file = f"store/song_recs/{interaction.user.id}.json"

        if os.path.exists(song_recs_file):
            embed = discord.Embed(description=f"You seem to have already created a song list, continuing will clear the list.\n\nAre you sure you want to continue?", color=0xFF0000)

            async def confirmation_callback(inter: discord.Interaction):
                if inter.custom_id == "warning:yes":
                    await inter.response.send_modal(CreateSongListDescriptionModal(inter.user))
                    await inter.delete_original_response()

                elif inter.custom_id == "warning:no":
                    await inter.response.edit_message(embed=discord.Embed(description="Cancelled creating a new song list.", color=0xFF0000), view=None)
                    return

            await interaction.response.send_message(embed=embed, view=WarningConfirmationView(interaction.user.id, confirmation_callback), ephemeral=True)
        else:
            await interaction.response.send_modal(CreateSongListDescriptionModal(interaction.user))

    @rand_song_group.command(name="edit", description="Edit your song list")
    async def edit_list(self, interaction: discord.Interaction):
        song_recs_file = f"store/song_recs/{interaction.user.id}.json"

        if not os.path.exists(song_recs_file):
            embed = discord.Embed(description=f"You don't have a song list yet. Use `/song_list create` to create one.", color=0xFF0000)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Plan: 30 songs per user, use embed description to display the list of songs, and use buttons to navigate through pages of songs. 10 songs per page.
        # Row 1: Previous Page, Next Page
        # Row 2: Add Song, Remove Song, Edit Song
        # If the user clicks Add Song, check if is over the limit and show a modal to add a song. 
        # If the user clicks Remove Song, change row 2 to dropdown menu (with songs on page) and row 3 to red remove button. 
        # If the user clicks Edit Song, change row 2 to dropdown menu (with songs on page) and row 3 to blue edit button. 

        embed = song_list_paginator(interaction.user, 0)
        await interaction.response.send_message(embed=embed, view=EditSongListPaginatorView(interaction.user, 0))


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun_Cog(bot))