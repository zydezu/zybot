import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import scripts.danboorusearch as danboorusearch

class DanbooruCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.allowed_contexts = app_commands.AppCommandContext(
            guild=True,
            dm_channel=True,
            private_channel=True
        )

    @app_commands.command(
        name="send-konata-x-kagami",
        description="Send a random konata x kagami image to chat from Danbooru!"
    )
    async def send_konata_x_kagami(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        print("[main] Sending a random Lucky Star image from danbooru")
        image_url = danboorusearch.get_image_url(
            os.getenv('DANBOORU_USERNAME'), 
            os.getenv('DANBOORU_API_KEY')
        )
        if image_url: 
            await interaction.followup.send(content=image_url)

    @app_commands.command(
        name="search-danbooru",
        description="Search Danbooru with parameters and get a random image from the results"
    )
    @app_commands.describe(
        query="""Search tags (eg: "izumi_konata hiiragi_kagami")""",
        rating="Content rating"
    )
    @app_commands.choices(rating=[
        app_commands.Choice(name="Safe", value="s"),
        app_commands.Choice(name="Questionable", value="q"),
        app_commands.Choice(name="Explicit", value="e")
    ])
    async def search_danbooru(
        self, 
        interaction: discord.Interaction, 
        query: str, 
        rating: app_commands.Choice[str] | None = None
    ):
        await interaction.response.defer(ephemeral=False)
        rating_value = rating.value if rating else "s"
        print(f"[main] Searching Danbooru with query: {query}, rating: {rating_value}")
        image_url = await asyncio.to_thread(
            danboorusearch.get_image_url,
            os.getenv('DANBOORU_USERNAME'),
            os.getenv('DANBOORU_API_KEY'),
            query,
            rating_value
        )
        if image_url: 
            await interaction.followup.send(content=image_url)
        else:
            await interaction.followup.send(content="No images found for the specified query.")

async def setup(bot):
    await bot.add_cog(DanbooruCog(bot))