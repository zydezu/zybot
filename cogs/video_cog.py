import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import embed as embed_module
import scripts.downloadvideo as downloadvideo

class VideoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="archive-video",
        description="Download a video using yt-dlp and generate a HTML file with it's details",
    )
    @app_commands.describe(
        link="The link of the video you want to download"
    )
    async def archive_video(self, interaction: discord.Interaction, link: str):
        await interaction.response.defer(ephemeral=False)

        message = await interaction.followup.send(
            embed=embed_module.show_download_progress(link)
        )

        result = await asyncio.to_thread(downloadvideo.startvideodownload, link)

        completed_embed = embed_module.show_download_complete(result)

        await message.edit(embed=completed_embed)

async def setup(bot):
    await bot.add_cog(VideoCog(bot))
