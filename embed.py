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
    embed.set_footer(text="Please wait while the video is being processed.")
    return embed

def show_download_complete(link):
    embed = discord.Embed(
        title="Downloaded Video",
        description=f"Your download has been completed successfully!",
        color=EMBED.GREEN
    )
    embed.set_footer(text=f"You can see it at: https://zyserver.hopto.org:9999/generated/{link}/")
    return embed