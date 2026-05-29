import asyncio
import os

import aiohttp
import discord
from discord.ext import commands

import scripts.danboorusearch as danboorusearch


class FunCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hi(self, ctx):
        try:
            await ctx.send("Hi!!")
        except aiohttp.ClientConnectionResetError:
            pass

    @commands.command()
    async def k(self, ctx):
        image_url = await asyncio.to_thread(
            danboorusearch.get_image_url,
            os.getenv("DANBOORU_USERNAME"),
            os.getenv("DANBOORU_API_KEY"),
        )
        if image_url:
            try:
                await ctx.send(image_url)
            except aiohttp.ClientConnectionResetError:
                pass

    @commands.command()
    async def pettan(self, ctx):
        try:
            await ctx.send(file=discord.File("media/music/つるぺったん.mp3"))
        except aiohttp.ClientConnectionResetError:
            pass


async def setup(bot):
    await bot.add_cog(FunCog(bot))
