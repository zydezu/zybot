import discord
from discord.ext import commands
import gitimport

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sync_tree(self, ctx):
        synced_list = await ctx.bot.tree.sync()
        await ctx.send(f"Syncing {len(synced_list)} commands to all guilds")

    @commands.command(
        name="shoot-and-kill-bot-grrrrr",
        description="Take the bot out back and restart the app"
    )
    @commands.has_permissions(administrator=True)
    async def shoot_and_kill_bot_grrrrr(self, ctx):
        await ctx.send("Restarting...")
        await self.bot.close()
        gitimport.restart_bot()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
