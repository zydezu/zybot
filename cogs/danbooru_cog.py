import asyncio
import os

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import scripts.danboorusearch as danboorusearch


class SearchAgainView(discord.ui.View):
    def __init__(
        self,
        post_url=None,
        query=None,
        rating="s",
        no_result_msg="No images found for the specified query.",
    ):
        super().__init__(timeout=600)
        self.query = query
        self.rating = rating
        self.no_result_msg = no_result_msg
        self.link_button: discord.ui.Button | None = None
        if post_url:
            self.link_button = discord.ui.Button(
                label="Open Link", style=discord.ButtonStyle.link, url=post_url
            )
            self.add_item(self.link_button)

    @discord.ui.button(label="Search Again", style=discord.ButtonStyle.secondary)
    async def search_again(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        try:
            args = [os.getenv("DANBOORU_USERNAME"), os.getenv("DANBOORU_API_KEY")]
            if self.query is not None:
                args += [self.query, self.rating]
            result = await asyncio.to_thread(danboorusearch.get_image_url, *args)
            image_url, post_url = result if result else (None, None)
            content = image_url if image_url else self.no_result_msg
            if post_url:
                if self.link_button is None:
                    self.link_button = discord.ui.Button(
                        label="Open Link", style=discord.ButtonStyle.link, url=post_url
                    )
                    self.add_item(self.link_button)
                else:
                    self.link_button.url = post_url
            await interaction.edit_original_response(content=content, view=self)
        except (aiohttp.ClientConnectionResetError, discord.errors.NotFound):
            pass

    @discord.ui.button(label="Delete Message", style=discord.ButtonStyle.danger)
    async def delete_message(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.message.delete()


class DanbooruCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="send-konata-x-kagami",
        description="Send a random konata x kagami image to chat from Danbooru!",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def send_konata_x_kagami(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        print("[main] Sending a random Lucky Star image from danbooru")
        try:
            result = await asyncio.to_thread(
                danboorusearch.get_image_url,
                os.getenv("DANBOORU_USERNAME"),
                os.getenv("DANBOORU_API_KEY"),
            )
            image_url, post_url = result if result else (None, None)
            content = image_url if image_url else "No images found for the specified query."
            await interaction.followup.send(content=content, view=SearchAgainView(post_url=post_url))
        except (aiohttp.ClientConnectionResetError, discord.errors.NotFound):
            pass

    @app_commands.command(
        name="search-danbooru",
        description="Search Danbooru with parameters and get a random image from the results",
    )
    @app_commands.describe(
        query="""Search tags (eg: "izumi_konata hiiragi_kagami")""",
        rating="Content rating",
    )
    @app_commands.choices(
        rating=[
            app_commands.Choice(name="Safe", value="s"),
            app_commands.Choice(name="Questionable", value="q"),
            app_commands.Choice(name="Explicit", value="e"),
        ]
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def search_danbooru(
        self,
        interaction: discord.Interaction,
        query: str,
        rating: app_commands.Choice[str] | None = None,
    ):
        await interaction.response.defer(ephemeral=False)
        rating_value = rating.value if rating else "s"
        print(f"[main] Searching Danbooru with query: {query}, rating: {rating_value}")
        try:
            result = await asyncio.to_thread(
                danboorusearch.get_image_url,
                os.getenv("DANBOORU_USERNAME"),
                os.getenv("DANBOORU_API_KEY"),
                query,
                rating_value,
            )
            image_url, post_url = result if result else (None, None)
            no_result_msg = "No images found for the specified query, view a list of tags [here](https://gist.githubusercontent.com/bem13/0bc5091819f0594c53f0d96972c8b6ff/raw/b0aacd5ea4634ed4a9f320d344cc1fe81a60db5a/danbooru_tags_post_count.csv)!"
            content = image_url if image_url else no_result_msg
            await interaction.followup.send(
                content=content,
                view=SearchAgainView(
                    post_url=post_url,
                    query=query,
                    rating=rating_value,
                    no_result_msg=no_result_msg,
                ),
            )
        except (aiohttp.ClientConnectionResetError, discord.errors.NotFound):
            pass


async def setup(bot):
    await bot.add_cog(DanbooruCog(bot))
