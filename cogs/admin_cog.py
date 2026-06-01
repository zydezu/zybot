import discord
import scripts.gitimport as gitimport
from discord import app_commands
from discord.ext import commands


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
            await channel.set_permissions(
                everyone, overwrite=overwrite, reason="Lockdown"
            )
            locked.append(channel.mention)

        for channel in guild.voice_channels:
            overwrite = channel.overwrites_for(everyone)
            overwrite.connect = False
            await channel.set_permissions(
                everyone, overwrite=overwrite, reason="Lockdown"
            )
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
                await channel.set_permissions(
                    everyone, overwrite=None, reason="Unlockdown"
                )
            else:
                await channel.set_permissions(
                    everyone, overwrite=overwrite, reason="Unlockdown"
                )
            unlocked.append(channel.mention)

        for channel in guild.voice_channels:
            overwrite = channel.overwrites_for(everyone)
            overwrite.connect = None
            if overwrite.is_empty():
                await channel.set_permissions(
                    everyone, overwrite=None, reason="Unlockdown"
                )
            else:
                await channel.set_permissions(
                    everyone, overwrite=overwrite, reason="Unlockdown"
                )
            unlocked.append(channel.mention)

        await interaction.followup.send(
            f"Unlocked {len(unlocked)} channel(s): {', '.join(unlocked)}",
            ephemeral=True,
        )

    @app_commands.command(
        name="purge-user",
        description="Delete all messages from a user in this channel or across all channels",
    )
    @app_commands.describe(user="The user to purge messages from (or paste their ID)")
    @app_commands.default_permissions(administrator=True)
    async def purge_user(
        self,
        interaction: discord.Interaction,
        user: discord.User,
    ):
        await interaction.response.defer(ephemeral=True)

        check = lambda m: m.author.id == user.id
        channels = interaction.guild.text_channels
        total = 0

        for channel in channels:
            try:
                deleted = await channel.purge(limit=None, check=check, bulk=True)
                total += len(deleted)
            except discord.Forbidden:
                pass

        await interaction.followup.send(
            f"Deleted {total} message(s) from {user.mention} across all channels.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
