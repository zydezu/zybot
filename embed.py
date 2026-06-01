import io
from datetime import datetime

import discord


class EMBED:
    STANDARD = 0xBC0839
    RED = 0xE0102F
    GREEN = 0x08A937
    LIGHT_GREEN = 0x71BF45
    LIGHT_BLUE = 0x27BCFC
    YELLOW = 0xFFE100
    PURPLE = 0x7289DA


def show_new_commit(
    repo, author, author_avatar_url, message, date, url, additions=None, deletions=None
):
    embed = discord.Embed(
        title=f"[{repo}] 1 new commit",
        description=message,
        color=EMBED.PURPLE,
        url=url,
    )

    embed.set_author(name=author, icon_url=author_avatar_url)

    if additions is not None and deletions is not None:
        stats_text = f"```diff\n+{additions} lines\n-{deletions} lines\n```"
        embed.description = f"{embed.description}\n{stats_text}"

    parsed_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
    formatted_date = parsed_date.strftime("%Y-%m-%d at %H:%M %Z")
    embed.set_footer(text=f"Committed on {formatted_date}")

    return embed


def show_accent_colour(hex_color, color_image):
    embed = discord.Embed(
        title="Accent Colour",
        description=f"**{hex_color}**",
        color=int(hex_color.replace("#", ""), 16),
    )

    image_bytes = io.BytesIO()
    color_image.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    embed.set_image(url="attachment://color.png")

    file = discord.File(image_bytes, filename="color.png")
    return embed, file


def show_lockdown(locked_channels, actor):
    embed = discord.Embed(
        title="Server Locked Down",
        description=f"Locked **{len(locked_channels)}** channel(s).\n\n{' '.join(locked_channels)}",
        color=EMBED.RED,
    )
    embed.set_footer(text=f"Locked by {actor}")
    return embed


def show_unlockdown(unlocked_channels, actor):
    embed = discord.Embed(
        title="Server Unlocked",
        description=f"Unlocked **{len(unlocked_channels)}** channel(s).\n\n{' '.join(unlocked_channels)}",
        color=EMBED.GREEN,
    )
    embed.set_footer(text=f"Unlocked by {actor}")
    return embed


def show_purge_user(user, total, actor):
    embed = discord.Embed(
        title="Messages Purged",
        description=f"Deleted **{total}** message(s) from {user.mention} across all channels.",
        color=EMBED.STANDARD,
    )
    embed.set_footer(text=f"Purged by {actor}")
    return embed


def show_restart(actor):
    embed = discord.Embed(
        title="Restarting...",
        description="The bot is restarting. Back in a moment.",
        color=EMBED.YELLOW,
    )
    embed.set_footer(text=f"Restarted by {actor}")
    return embed


def show_new_repo(repo, owner_name, owner_avatar_url, url, is_fork, description=None):
    embed = discord.Embed(
        title=f"New Repository {is_fork and 'Forked' or 'Created'}: {repo}",
        description=description or "No description provided",
        color=EMBED.PURPLE if not is_fork else EMBED.LIGHT_BLUE,
        url=url,
    )

    embed.set_author(name=owner_name, icon_url=owner_avatar_url)
    embed.add_field(name="Owner", value=owner_name, inline=True)

    parsed_date = datetime.now()
    formatted_date = parsed_date.strftime("%Y-%m-%d at %H:%M %Z")
    embed.set_footer(text=f"Detected on {formatted_date}")

    return embed
