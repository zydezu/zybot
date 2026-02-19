import discord, io

class EMBED:
    STANDARD = 0xbc0839
    RED = 0xe0102f
    GREEN = 0x08a937
    LIGHT_GREEN = 0x71bf45
    LIGHT_BLUE = 0x27bcfc
    YELLOW = 0xffe100
    PURPLE = 0x7289da

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

def show_accent_colour(hex_color, color_image):
    embed = discord.Embed(
        title="Accent Colour",
        description=f"**{hex_color}**",
        color=int(hex_color.replace('#', ''), 16)
    )
    
    image_bytes = io.BytesIO()
    color_image.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    embed.set_image(url="attachment://color.png")
    
    file = discord.File(image_bytes, filename="color.png")
    return embed, file