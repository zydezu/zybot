import re

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import ImageColor

import embed as embed_module

COLOUR_ROLE_PREFIX = "🎨 "
BARE_HEX_RE = re.compile(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}")


def parse_colour(text):
    """Return (hex_color, (r, g, b)) for a hex code, CSS colour name or
    rgb()/hsl() string, or None if it can't be understood."""
    spec = text.strip()
    if BARE_HEX_RE.fullmatch(spec):
        spec = "#" + spec
    try:
        rgb = ImageColor.getrgb(spec)
    except ValueError:
        return None
    rgb = tuple(rgb[:3])
    hex_color = "#{:02X}{:02X}{:02X}".format(*rgb)
    return hex_color, rgb


def colour_roles_of(member):
    return [r for r in member.roles if r.name.startswith(COLOUR_ROLE_PREFIX)]


async def purge_unused(roles, keeper):
    """Delete colour roles that nobody except `keeper` still holds."""
    for r in roles:
        if not any(m.id != keeper.id for m in r.members):
            try:
                await r.delete(reason="Unused colour role")
            except (discord.Forbidden, discord.HTTPException):
                pass


async def safe_followup(interaction, **kwargs):
    try:
        await interaction.followup.send(**kwargs)
    except aiohttp.ClientConnectionResetError:
        pass


class ColourCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _need_manage_roles(self, interaction):
        if interaction.guild.me.guild_permissions.manage_roles:
            return True
        await interaction.response.send_message(
            "I need the **Manage Roles** permission to do that.", ephemeral=True
        )
        return False

    @app_commands.command(
        name="add-colour",
        description="Give yourself a role in the colour/color you pick (hex or CSS colour name)",
    )
    @app_commands.describe(
        colour='A hex code like "#ff8800" or "f80", a CSS name like "cornflowerblue", or "rgb(0,120,255)"'
    )
    @app_commands.guild_only()
    async def add_colour(self, interaction: discord.Interaction, colour: str):
        parsed = parse_colour(colour)
        if parsed is None:
            await interaction.response.send_message(
                f"Couldn't understand `{colour}`. Try a hex code like `#ff8800` or a colour name like `teal`.",
                ephemeral=True,
            )
            return
        if not await self._need_manage_roles(interaction):
            return

        hex_color, rgb = parsed
        guild = interaction.guild
        me = guild.me
        member = interaction.user

        await interaction.response.defer()

        role_name = f"{COLOUR_ROLE_PREFIX}{hex_color}"
        role = discord.utils.get(guild.roles, name=role_name)
        created = role is None
        if created:
            role = await guild.create_role(
                name=role_name,
                # Discord renders a role colour of 0 as no colour
                colour=discord.Colour.from_rgb(*(rgb if any(rgb) else (1, 1, 1))),
                reason=f"Colour role requested by {member}",
            )

        # everytime i try to have a discord bot create a role, it goes badly and i cry
        target_position = max(1, me.top_role.position - 1)
        if role.position != target_position:
            try:
                await guild.edit_role_positions({role: target_position})
            except (discord.Forbidden, discord.HTTPException) as exc:
                print(f"[main] Couldn't move {role.name} to {target_position}: {exc}")

        # [-1] is the highest role (aigis)
        not_at_top = me.top_role.id != guild.roles[-1].id

        old_roles = [r for r in colour_roles_of(member) if r.id != role.id]
        if old_roles:
            await member.remove_roles(*old_roles, reason="Switching colour role")
        if role not in member.roles:
            await member.add_roles(role, reason="Colour role")
        await purge_unused(old_roles, member)

        embed, file = embed_module.show_colour_role(
            hex_color, rgb, role, member.display_name, created
        )
        content = (
            f"Note: move my **{me.top_role.name}** role to the top of "
            "Server Settings → Roles so colour roles can sit above the rest."
            if not_at_top
            else None
        )
        await safe_followup(interaction, content=content, embed=embed, file=file)

    @app_commands.command(
        name="remove-colour",
        description="Remove the colour role you gave yourself",
    )
    @app_commands.guild_only()
    async def remove_colour(self, interaction: discord.Interaction):
        member = interaction.user
        colour_roles = colour_roles_of(member)
        if not colour_roles:
            await interaction.response.send_message(
                "You don't have a colour role.", ephemeral=True
            )
            return
        if not await self._need_manage_roles(interaction):
            return

        await interaction.response.defer(ephemeral=True)
        await member.remove_roles(*colour_roles, reason="Removing colour role")
        await purge_unused(colour_roles, member)

        names = ", ".join(f"`{r.name}`" for r in colour_roles)
        await safe_followup(interaction, content=f"Removed {names}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ColourCog(bot))
