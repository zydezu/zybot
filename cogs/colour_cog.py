import re

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import ImageColor

import embed as embed_module

COLOUR_ROLE_PREFIX = "🎨 "
BARE_HEX_RE = re.compile(r"^[0-9a-fA-F]{3}$|^[0-9a-fA-F]{6}$")


def parse_colour(text):
    """Return (hex_color, (r, g, b)) for a hex code, CSS colour name or
    rgb()/hsl() string, or None if it can't be understood."""
    spec = text.strip()
    if BARE_HEX_RE.match(spec):
        spec = "#" + spec
    try:
        rgb = ImageColor.getrgb(spec)
    except ValueError:
        return None
    rgb = tuple(rgb[:3])
    hex_color = "#{:02X}{:02X}{:02X}".format(*rgb)
    return hex_color, rgb


class ColourCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        hex_color, rgb = parsed
        guild = interaction.guild
        me = guild.me

        if not me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "I need the **Manage Roles** permission to do that.", ephemeral=True
            )
            return

        await interaction.response.defer()

        role_name = f"{COLOUR_ROLE_PREFIX}{hex_color}"
        # Discord renders a role colour of 0 as no colour
        role_colour = discord.Colour.from_rgb(*(rgb if any(rgb) else (1, 1, 1)))

        role = discord.utils.get(guild.roles, name=role_name)
        created = False
        if role is None:
            role = await guild.create_role(
                name=role_name,
                colour=role_colour,
                reason=f"Colour role requested by {interaction.user}",
            )
            created = True

        # Keep colour roles as high as possible (just under my top role, which
        # is as far up as Discord lets me move them) so the colour actually
        # shows. Do this for existing roles too, not just freshly created ones.
        target_position = max(1, me.top_role.position - 1)
        if role.position != target_position:
            try:
                # edit_role_positions is the bulk endpoint and actually moves
                # the role; Role.edit(position=...) can silently no-op.
                await guild.edit_role_positions({role: target_position})
            except (discord.Forbidden, discord.HTTPException) as exc:
                print(f"[main] Couldn't move {role.name} to position {target_position}: {exc}")

        # A bot can never place a role above its own highest role, so if my role
        # isn't at the very top of the list the colour role can't be either.
        highest = max(guild.roles, key=lambda r: r.position)
        not_at_top = me.top_role.id != highest.id

        member = interaction.user
        old_roles = [
            r
            for r in member.roles
            if r.name.startswith(COLOUR_ROLE_PREFIX) and r.id != role.id
        ]
        if old_roles:
            await member.remove_roles(*old_roles, reason="Switching colour role")
        if role not in member.roles:
            await member.add_roles(role, reason="Colour role")

        # Clean up colour roles nobody is using anymore.
        for r in old_roles:
            if not [m for m in r.members if m.id != member.id]:
                try:
                    await r.delete(reason="Unused colour role")
                except (discord.Forbidden, discord.HTTPException):
                    pass

        embed, file = embed_module.show_colour_role(
            hex_color, rgb, role, member.display_name, created
        )
        content = None
        if not_at_top:
            content = (
                f"Note: move my **{me.top_role.name}** role to the top of "
                "Server Settings → Roles so colour roles can sit above the rest."
            )
        try:
            await interaction.followup.send(content=content, embed=embed, file=file)
        except aiohttp.ClientConnectionResetError:
            pass

    @app_commands.command(
        name="remove-colour",
        description="Remove the colour role you gave yourself",
    )
    @app_commands.guild_only()
    async def remove_colour(self, interaction: discord.Interaction):
        member = interaction.user
        colour_roles = [
            r for r in member.roles if r.name.startswith(COLOUR_ROLE_PREFIX)
        ]
        if not colour_roles:
            await interaction.response.send_message(
                "You don't have a colour role.", ephemeral=True
            )
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "I need the **Manage Roles** permission to do that.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        await member.remove_roles(*colour_roles, reason="Removing colour role")

        # Clean up colour roles nobody is using anymore.
        for r in colour_roles:
            if not [m for m in r.members if m.id != member.id]:
                try:
                    await r.delete(reason="Unused colour role")
                except (discord.Forbidden, discord.HTTPException):
                    pass

        names = ", ".join(f"`{r.name}`" for r in colour_roles)
        try:
            await interaction.followup.send(f"Removed {names}.", ephemeral=True)
        except aiohttp.ClientConnectionResetError:
            pass


async def setup(bot):
    await bot.add_cog(ColourCog(bot))
