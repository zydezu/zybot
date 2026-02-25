import os
import discord
from discord import app_commands
from discord.ext import commands
import scripts.danboorusearch as danboorusearch
import scripts.graphics as graphics
import embed as embed_module

class FunCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="accentcolour",
        description="Get the accent colour of a user's avatar"
    )
    @app_commands.describe(
        user="The user to get the accent colour from (optional)"
    )
    async def accentcolour(self, interaction: discord.Interaction, user: discord.User | None = None):
        target_user = user or interaction.user
        hex_color, color_image = graphics.get_accent_colour(target_user)
        embed_to_send, file = embed_module.show_accent_colour(hex_color, color_image)
        await interaction.response.send_message(embed=embed_to_send, file=file)

    @commands.command()
    async def hi(self, ctx):
        await ctx.send("Hi!!")

    @commands.command()
    async def k(self, ctx):
        image_url = danboorusearch.get_image_url(
            os.getenv('DANBOORU_USERNAME'), 
            os.getenv('DANBOORU_API_KEY')
        )
        if image_url: 
            await ctx.send(image_url)

    @commands.command()
    async def pettan(self, ctx):
        await ctx.send(file=discord.File("media/music/つるぺったん.mp3"))

async def setup(bot):
    await bot.add_cog(FunCog(bot))
