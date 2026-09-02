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
        name="colour",
        description="Give yourself a role in the colour/color you pick (hex or CSS colour name)",
    )
    @app_commands.describe(
        colour='A hex code like "#ff8800" or "f80", a CSS name like "cornflowerblue", or "rgb(0,120,255)"'
    )
    @app_commands.guild_only()
    async def colour(self, interaction: discord.Interaction, colour: str):
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
            try:
                await role.edit(position=max(1, me.top_role.position - 1))
            except (discord.Forbidden, discord.HTTPException):
                pass

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
        try:
            await interaction.followup.send(embed=embed, file=file)
        except aiohttp.ClientConnectionResetError:
            pass


async def setup(bot):
    await bot.add_cog(ColourCog(bot))
