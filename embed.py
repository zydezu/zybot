import io

import discord


class EMBED:
    STANDARD = 0xBC0839
    RED = 0xE0102F
    GREEN = 0x08A937
    LIGHT_GREEN = 0x71BF45
    LIGHT_BLUE = 0x27BCFC
    YELLOW = 0xFFE100
    PURPLE = 0x7289DA


def show_download_progress(link):
    embed = discord.Embed(
        title="Downloading Video",
        description=f"The video is being downloaded from: {link}",
        color=EMBED.YELLOW,
    )
    embed.set_footer(text="Please wait while the video is being processed")
    return embed


def show_download_complete(link):
    embed = discord.Embed(
        title="Downloaded Video",
        description="The download has been completed successfully!",
        color=EMBED.GREEN,
    )
    return embed


def show_new_commit(
    repo,
    author,
    author_avatar_url,
    message,
    date,
    url,
    additions=None,
    deletions=None,
    summary=None,
):
    if summary:
        description = f"**{summary}**\n_{message}_"
    else:
        description = message

    embed = discord.Embed(
        title=f"[{repo}] 1 new commit",
        description=description,
        color=EMBED.PURPLE,
        url=url,
    )

    embed.set_author(name=author, icon_url=author_avatar_url)

    if additions is not None and deletions is not None:
        stats_text = f"```diff\n+{additions} -{deletions} lines\n```"
        embed.description = f"{embed.description}\n{stats_text}"

    embed.set_footer(text=f"Committed on {date}")

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
