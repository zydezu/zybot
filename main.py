import hashlib
import os
import random
from multiprocessing import freeze_support

import aiohttp
import discord
from discord.ext import commands, tasks

import scripts.artcounting as artcounting
import scripts.commits as commits
import scripts.danboorusearch as danboorusearch
import scripts.llm as llm
from config import (
    CHANNEL_IDS,
    CHANNELS_TO_COUNT,
    LUCKY_STAR_LINES_PATH,
    SEND_GIT_COMMITS,
    TOKEN,
    URL_REGEX,
    ZYBOT_ID,
)
from scripts.message_utils import convert_images_to_avif, convert_links_to_embed

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
intents.dm_messages = True
bot = commands.Bot(command_prefix="zy!", intents=intents)


class BotState:
    def __init__(self):
        self.conversation_context = []
        self.lucky_star_lines = []
        self.recent_image_hashes = []
        self.lucky_star_loaded = False

    def add_to_context(self, author, message):
        self.conversation_context.append((author, message))
        if len(self.conversation_context) > 25:
            self.conversation_context.pop(0)

    def get_lucky_star_line(self):
        if not self.lucky_star_loaded:
            with open(LUCKY_STAR_LINES_PATH, "r", encoding="utf8") as f:
                self.lucky_star_lines.extend(f.readlines())
            self.lucky_star_loaded = True
        return random.choice(self.lucky_star_lines).strip()

    def check_duplicate_image(self, url):
        img_hash = hashlib.md5(url.encode()).hexdigest()
        if img_hash in self.recent_image_hashes:
            return True
        self.recent_image_hashes.append(img_hash)
        if len(self.recent_image_hashes) > 25:
            self.recent_image_hashes.pop(0)
        return False


state = BotState()


@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online, activity=discord.Game("Playing Persona 3 FES")
    )

    await bot.load_extension("cogs.video_cog")
    await bot.load_extension("cogs.danbooru_cog")
    await bot.load_extension("cogs.admin_cog")
    await bot.load_extension("cogs.fun_cog")

    await bot.tree.sync()
    print("[main] Synced commands globally")

    check_commits.start()
    await check_commits()
    print(f"[main] Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_guild_join(guild):
    await bot.tree.sync(guild=guild)
    print(f"[main] Synced commands for new guild: {guild.name} (ID: {guild.id})")


async def handle_ai_response(message):
    state.add_to_context(message.author.display_name, message.content)
    async with message.channel.typing():
        llm_data = llm.generate_content_llm(
            message.content, message.author.display_name, state.conversation_context
        )
        try:
            await message.reply(llm_data)
        except aiohttp.ClientConnectionResetError:
            pass


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    if isinstance(message.channel, discord.DMChannel):
        print(f"[main] DM from {message.author}: {content}")
        await handle_ai_response(message)
        await bot.process_commands(message)
        return

    print(f"[main] Processing {content}")

    category = CHANNELS_TO_COUNT.get(message.channel.name)
    if category and URL_REGEX.fullmatch(content):
        if "discord.com" not in content and "tenor.com" not in content:
            artcounting.increment_user_artcount(message.author.id, category)

    should_respond = False

    if any(user.id == ZYBOT_ID for user in message.mentions):
        should_respond = True
    elif message.reference and message.reference.message_id:
        replied_message = message.reference.resolved
        if replied_message and replied_message.author.id == ZYBOT_ID:
            should_respond = True

    if should_respond:
        await handle_ai_response(message)

    if message.channel.name == "general" and not message.reference:
        rand = random.random()

        if rand < 0.002:
            await handle_ai_response(message)
        elif rand < 0.02:
            print("[main] Sending a random Lucky Star quote")
            try:
                await message.channel.send(state.get_lucky_star_line())
            except aiohttp.ClientConnectionResetError:
                pass
        elif rand < 0.04:
            print("[main] Sending a random Lucky Star image from danbooru")
            image_url = danboorusearch.get_image_url(
                os.getenv("DANBOORU_USERNAME"), os.getenv("DANBOORU_API_KEY")
            )
            if image_url and not state.check_duplicate_image(image_url):
                try:
                    await message.channel.send(image_url)
                except aiohttp.ClientConnectionResetError:
                    pass
        elif rand < 0.025:
            await convert_images_to_avif(message)

    if content:
        new_link, converted = convert_links_to_embed(content)
        if converted:
            try:
                await message.edit(suppress=True)
            except aiohttp.ClientConnectionResetError:
                pass
            else:
                try:
                    await message.reply(new_link, mention_author=False)
                except aiohttp.ClientConnectionResetError:
                    pass

    await bot.process_commands(message)


@tasks.loop(minutes=1)
async def check_commits():
    if SEND_GIT_COMMITS:
        channel = bot.get_channel(CHANNEL_IDS.get("git-commits"))
        new_commit_embeds = commits.check_commits(
            os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_USERNAME")
        )
        for commit in new_commit_embeds:
            try:
                await channel.send(embed=commit)
            except aiohttp.ClientConnectionResetError:
                pass


@bot.command()
async def sync_tree(ctx):
    synced = await bot.tree.sync()
    try:
        await ctx.send(f"Synced {synced} - {len(synced)} commands globally.")
    except aiohttp.ClientConnectionResetError:
        pass


def main():
    bot.run(token=TOKEN)


if __name__ == "__main__":
    freeze_support()
    main()
