import embed, downloadvideo, gitimport
import os, io, asyncio, functools, aiohttp
from dotenv import load_dotenv
from multiprocessing import freeze_support
from PIL import Image
from discord.ext import commands
from discord import app_commands
import discord

os.system("") # Needed for message to have colour in the terminal

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
channel_ids = {
    "youtube-logs": 1391985272589123665
}

# ---------------
# BOT SETUP
# ---------------
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="zy!", intents=intents)

### ====== Slash commands ======
@bot.tree.command(
    name="generatepage",
    description="Download a video and generate a page with the video and its details.",
)
@app_commands.describe(
    link="The link of the video you want to download"
)
@commands.has_permissions(administrator=True)
async def generatepage(interaction: discord.Interaction, link: str):
    await interaction.response.defer(ephemeral=False)

    message = await interaction.followup.send(
        embed=embed.show_download_progress(link)
    )

    # Run the blocking download in a separate thread so it doesn't block the event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, functools.partial(downloadvideo.startvideodownload, link))

    completed_embed = embed.show_download_complete(result)

    await message.edit(embed=completed_embed)

@bot.tree.command(
    name="restart",
    description="Restart the app"
)
@commands.has_permissions(administrator=True)
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message("Restarting...")
    await bot.close()
    gitimport.restart_bot()

### ====== Test commands ======
@bot.command()
@commands.has_permissions(administrator=True)
async def sync_tree(ctx):
    synced_list = await ctx.bot.tree.sync()
    await ctx.send(f"Syncing {len(synced_list)} commands to all guilds")

@bot.command()
async def hi(ctx):
    await ctx.send("Hi!!")

### ====== Bot ======
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})\n')

@bot.event
async def on_message(message):
    # Prevent bot from responding to itself
    if message.author.bot:
        return

    # Check if there is an attachment
    if message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ["png", "jpg", "jpeg", "bmp", "webp"]):
                await convert_to_avif(message, attachment)

    await bot.process_commands(message)  # Keep commands working

async def convert_to_avif(message, attachment):
    print("Converting...")

    print("Attachment URL:", attachment.url)

    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(attachment.url) as resp:
            print("HTTP status:", resp.status)
            if resp.status != 200:
                print("Failed to download the image.")
                return
            data = await resp.read()

    # Open image with Pillow
    img = Image.open(io.BytesIO(data))

    # Convert to AVIF in memory with lowest quality
    avif_buffer = io.BytesIO()
    img.save(avif_buffer, format="AVIF", quality=0)
    avif_buffer.seek(0)

    # Send back
    await message.channel.send(file=discord.File(fp=avif_buffer, filename=f"{attachment.filename}.avif"))

### ====== Start bot ======
def main():
    bot.run(token=TOKEN)

if __name__ ==  "__main__":
    freeze_support()
    main()