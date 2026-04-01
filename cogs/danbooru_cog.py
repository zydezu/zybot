import os
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
import scripts.danboorusearch as danboorusearch

class DanbooruCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="send-konata-x-kagami",
        description="Send a random konata x kagami image to chat from Danbooru!"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def send_konata_x_kagami(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        print("[main] Sending a random Lucky Star image from danbooru")
        image_url = danboorusearch.get_image_url(
            os.getenv('DANBOORU_USERNAME'), 
            os.getenv('DANBOORU_API_KEY')
        )
        if image_url: 
            try:
                await interaction.followup.send(content=image_url)
            except aiohttp.ClientConnectionResetError:
                pass
        else:
            try:
                await interaction.followup.send(content="No images found for the specified query.")
            except aiohttp.ClientConnectionResetError:
                pass

async def setup(bot):
    await bot.add_cog(DanbooruCog(bot))