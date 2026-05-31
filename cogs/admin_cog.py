import discord
from discord import app_commands
from discord.ext import commands

import scripts.gitimport as gitimport


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="shoot-and-kill-bot-grrrrr",
        description="Take the bot out back and restart the app",
    )
    @commands.has_permissions(administrator=True)
    async def shoot_and_kill_bot_grrrrr(self, interaction: discord.Interaction):
        await interaction.response.send_message("Restarting...")
        await self.bot.close()
        gitimport.restart_bot()

    @app_commands.command(
        name="lockdown",
        description="Lock all channels except general (deny @everyone from sending messages)",
    )
    @app_commands.default_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        everyone = guild.default_role
        locked = []

        for channel in guild.text_channels:
            if channel.name == "general":
                continue
            overwrite = channel.overwrites_for(everyone)
            overwrite.send_messages = False
            await channel.set_permissions(everyone, overwrite=overwrite, reason="Lockdown")
            locked.append(channel.mention)

        await interaction.followup.send(
            f"Locked {len(locked)} channel(s): {', '.join(locked)}", ephemeral=True
        )

    @app_commands.command(
        name="unlockdown",
        description="Unlock all channels (restore @everyone send messages permission)",
    )
    @app_commands.default_permissions(administrator=True)
    async def unlockdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        everyone = guild.default_role
        unlocked = []

        for channel in guild.text_channels:
            if channel.name == "general":
                continue
            overwrite = channel.overwrites_for(everyone)
            overwrite.send_messages = None
            if overwrite.is_empty():
                await channel.set_permissions(everyone, overwrite=None, reason="Unlockdown")
            else:
                await channel.set_permissions(everyone, overwrite=overwrite, reason="Unlockdown")
            unlocked.append(channel.mention)

        await interaction.followup.send(
            f"Unlocked {len(unlocked)} channel(s): {', '.join(unlocked)}", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
