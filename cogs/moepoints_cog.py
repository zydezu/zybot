import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import embed as embed_module
import scripts.moepoints as moepoints


def _member_name(user, guild):
    """Prefer the guild nickname, fall back to global name."""
    if guild is not None:
        member = guild.get_member(user.id)
        if member is not None and member.nick:
            return member.nick
    return user.display_name or user.name


class MoePointsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="moe-points",
        description="How many moe points do you have?",
    )
    @app_commands.describe(user="whose points to check (defaults to you)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def moe_points(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ):
        target = user or interaction.user
        name = _member_name(target, interaction.guild)
        entry = moepoints.get_user_entry(target.id)

        if not entry:
            description = (
                f"**{name}** has no moe points at all. Not one. Ever. "
                "A blank slate."
            )
        else:
            points = int(entry.get("points", 0))
            best = entry.get("best") or {}
            description = f"**{name}** has **{points}** moe points"
            if best.get("points"):
                description += (
                    f"\nBiggest single award: **{best['points']}** points"
                    + (
                        f"\n{best['reason']}"
                        if best.get("reason")
                        else ""
                    )
                )

        try:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Moe Points",
                    description=description,
                    color=embed_module.EMBED.PURPLE,
                )
            )
        except aiohttp.ClientConnectionResetError:
            pass

    @app_commands.command(
        name="moe-leaderboard",
        description="The moe points leaderboard",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def moe_leaderboard(self, interaction: discord.Interaction):
        ranked = moepoints.leaderboard(10)

        if not ranked:
            description = "Nobody has any moe points yet. Embarrassing, honestly."
        else:
            medals = {1: "1st", 2: "2nd", 3: "3rd"}
            lines = []
            for position, (user_id, info) in enumerate(ranked, start=1):
                name = info["name"] or f"<@{user_id}>"
                marker = medals.get(position, f"{position}th")
                lines.append(f"**{marker}** — {name}: **{info['points']}**")
            description = "\n".join(lines)

        try:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Moe Points Leaderboard",
                    description=description,
                    color=embed_module.EMBED.YELLOW,
                )
            )
        except aiohttp.ClientConnectionResetError:
            pass


async def setup(bot):
    await bot.add_cog(MoePointsCog(bot))
