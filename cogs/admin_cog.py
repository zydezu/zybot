import discord
from discord.ext import commands
from discord import app_commands
import scripts.gitimport as gitimport

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="sync-tree",
        description="Sync slash commands to all guilds"
    )
    @app_commands.default_permissions(administrator=True)
    async def sync_tree(self, interaction: discord.Interaction):
        synced_list = await self.bot.tree.sync()
        await interaction.response.send_message(f"Synced {len(synced_list)} commands to all guilds")

    @app_commands.command(
        name="shoot-and-kill-bot-grrrrr",
        description="Take the bot out back and restart the app"
    )
    @commands.has_permissions(administrator=True)
    async def shoot_and_kill_bot_grrrrr(self, interaction: discord.Interaction):
        await interaction.response.send_message("Restarting...")
        await self.bot.close()
        gitimport.restart_bot()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))