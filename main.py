import embed, downloadvideo, gitimport, llm, getkonataxkagami
import os, io, asyncio, functools, aiohttp, random
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

LUCKYSTARLINESPATH = "luckystar/lines.txt"
conversation_context = []

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

@bot.command()
async def k(ctx):
    image_url = getkonataxkagami.get_image_url()
    if image_url: await ctx.send(image_url)

### ====== Bot ======
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})\n')

@bot.event
async def on_message(message):
    # Prevent bot from responding to itself
    if message.author.bot:
        return
    
    conversation_context.append(f"{message.author.display_name}: {message.content}")

    if random.random() < 0.2:
        with open(LUCKYSTARLINESPATH, "r", encoding="utf8") as f:
            luckystarlines = f.readlines()
            randomline = random.choice(luckystarlines).strip()
            await message.channel.send(randomline)
        return
    
    if random.random() < 0.8:
        async with message.channel.typing():
            llm_data = llm.generate_content_llm(message.content, message.author.display_name, conversation_context)
            conversation_context.append(f"Aigis: {llm_data}")
            await message.channel.send(llm_data)
        return

    if random.random() < 0.1:
        await convert_images_to_avif(message)
        return
    
    if random.random() < 0.4:
        image_url = getkonataxkagami.get_image_url()
        if image_url: await message.channel.send(image_url)
        return

    await bot.process_commands(message)  # Keep commands working

async def convert_images_to_avif(message):
    if not message.attachments:
        return

    original_text = message.content or ""

    print(f"Converting images in message to avif")

    avif_files = []

    for attachment in message.attachments:
        # Only process image files
        if not any(attachment.filename.lower().endswith(ext) for ext in ["png", "jpg", "jpeg", "bmp", "webp", "avif"]):
            continue

        # Download image
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    print("Failed to download the image.")
                    return
                data = await resp.read()

        os.makedirs("images", exist_ok=True)
        local_path = os.path.join("images", attachment.filename)
        with open(local_path, "wb") as f:
            f.write(data)

        # Convert to avif
        img = Image.open(io.BytesIO(data))
        avif_buffer = io.BytesIO()
        img.save(avif_buffer, format="AVIF", quality=0)
        avif_buffer.seek(0)

        # Send new image
        filename_no_ext = os.path.splitext(attachment.filename)[0]
        avif_filename = f"{filename_no_ext}.avif"
        avif_files.append(discord.File(fp=avif_buffer, filename=avif_filename))

    if avif_files:
        await message.channel.send(content=original_text, files=avif_files)
        
        # Delete original message
        try:
            await message.delete()
            print("Original message deleted")
        except discord.Forbidden:
            print("Missing permissions to delete the original message")
        except discord.NotFound:
            print("Original message already deleted")

### ====== Start bot ======
def main():
    bot.run(token=TOKEN)

if __name__ ==  "__main__":
    freeze_support()
    main()