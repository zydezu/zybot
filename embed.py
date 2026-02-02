import discord

class EMBED:
    STANDARD = 0xbc0839
    RED = 0xe0102f
    GREEN = 0x08a937
    LIGHT_GREEN = 0x71bf45
    LIGHT_BLUE = 0x27bcfc
    YELLOW = 0xffe100

def show_download_progress(link):
    embed = discord.Embed(
        title="Downloading Video",
        description=f"Your video is being downloaded from: {link}",
        color=EMBED.YELLOW
    )
    embed.set_footer(text="Please wait while the video is being processed")
    return embed

def show_download_complete(link):
    embed = discord.Embed(
        title="Downloaded Video",
        description=f"Your download has been completed successfully!",
        color=EMBED.GREEN
    )
    embed.set_footer(text=f"It will be stored on the zy archive")
    return embed

def show_new_commit(repo, author, message, date, url):
    embed = discord.Embed(
        title=f"New commit in {repo} by {author}",
        description=message,
        color=EMBED.GREEN,
        url=url
    )
    embed.set_footer(text=date)
    return embed