import embed, downloadvideo, gitimport, llm, danboorusearch, artcounting, commits, graphics
import os, asyncio, aiohttp, random, re, io
from config import (
    TOKEN, ZYBOTID, COMMITS_CHANNEL_ID, 
    LUCKYSTARLINESPATH, CHANNELS_TO_COUNT, URL_REGEX
)
from utils.message_utils import convert_links_to_embed, convert_images_to_avif
from multiprocessing import freeze_support
from PIL import Image
from discord.ext import tasks, commands
from discord import app_commands
import discord

os.system("") # Needed for message to have colour in the terminal

conversation_context = []
LUCKY_STAR_LINES = []

# ---------------
# BOT SETUP
# ---------------
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
intents.dm_messages = True
bot = commands.Bot(command_prefix="zy!", intents=intents)

### ====== Bot ======
@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("Playing Persona 3 FES"))
    
    await bot.load_extension("cogs.video_cog")
    await bot.load_extension("cogs.danbooru_cog")
    await bot.load_extension("cogs.admin_cog")
    await bot.load_extension("cogs.fun_cog")
    
    check_commits.start()
    await check_commits()
    print(f"[main] Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if isinstance(message.channel, discord.DMChannel):
        print(f"[main] DM from {message.author}: {message.content}")
        async with message.channel.typing():
            llm_data = llm.generate_content_llm(message.content, message.author.display_name, [])
            await message.reply(llm_data)
        await bot.process_commands(message)
        return
    
    print(f"[main] Processing {message.content}")

    category = CHANNELS_TO_COUNT.get(message.channel.name)
    if category:
        content = message.content.strip()
        
        if URL_REGEX.fullmatch(content):
            if "discord.com" not in content and "tenor.com" not in content:
                artcounting.increment_user_artcount(message.author.id, category)

    if any(user.id == ZYBOTID for user in message.mentions):
        async with message.channel.typing():
            llm_data = llm.generate_content_llm(message.content, message.author.display_name, [])
            await message.reply(llm_data)
    elif message.reference and message.reference.message_id:
        replied_message = message.reference.resolved
        if replied_message and replied_message.author.id == ZYBOTID:
            async with message.channel.typing():
                llm_data = llm.generate_content_llm(message.content, message.author.display_name, [])
                await message.reply(llm_data)

    if message.channel.name == "general":
        conversation_context.append(f"{message.author.display_name}: {message.content}")
        if len(conversation_context) > 100:
            conversation_context.pop(0)

        rand = random.random()
        if not (message.reference and message.reference.message_id) and rand < 0.002:
            async with message.channel.typing():
                llm_data = llm.generate_content_llm(message.content, message.author.display_name, conversation_context)
                await message.channel.send(llm_data)
        elif rand < 0.02:
            print("[main] Sending a random Lucky Star quote")
            if not LUCKY_STAR_LINES:
                with open(LUCKYSTARLINESPATH, "r", encoding="utf8") as f:
                    LUCKY_STAR_LINES.extend(f.readlines())
            randomline = random.choice(LUCKY_STAR_LINES).strip()
            await message.channel.send(randomline)
        elif rand < 0.05:
            print("[main] Sending a random Lucky Star image from danbooru")
            image_url = danboorusearch.get_image_url(os.getenv('DANBOORU_USERNAME'), os.getenv('DANBOORU_API_KEY'))
            if image_url: await message.channel.send(image_url)
        elif rand < 0.022:
            await convert_images_to_avif(message)

    if message.content:
        new_link, converted = convert_links_to_embed(message.content)
        if converted:
            await message.edit(suppress=True)
            await message.reply(new_link, mention_author=False)

    await bot.process_commands(message)  # Keep commands working

@tasks.loop(minutes=1)
async def check_commits():
    channel = bot.get_channel(COMMITS_CHANNEL_ID)

    new_commit_embeds = commits.check_commits(os.getenv('GITHUB_TOKEN'), os.getenv('GITHUB_USERNAME'))

    for commit in new_commit_embeds:
        await channel.send(embed=commit)

### ====== Start bot ======
def main():
    bot.run(token=TOKEN)

if __name__ ==  "__main__":
    freeze_support()
    main()