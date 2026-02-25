import re
import os
import io
import aiohttp
from PIL import Image
import discord
from config import EMBED_LINKS

def convert_links_to_embed(message):
    new_message = message
    converted = False

    for original, embed_link in EMBED_LINKS:
        pattern = re.compile(
            rf"(https?://)?(www\.)?{re.escape(original)}(?=[/?#]|$)",
            flags=re.IGNORECASE
        )

        def replace_domain(match, embed_link=embed_link):
            scheme = match.group(1) or ""
            return f"{scheme}{embed_link}"

        new_message, num_subs = pattern.subn(replace_domain, new_message)
        if num_subs:
            converted = True

    return new_message, converted


async def convert_images_to_avif(message):
    if not message.attachments:
        return

    original_text = message.content or ""

    print(f"[main] Converting images in message to avif")

    avif_files = []

    for attachment in message.attachments:
        if not any(attachment.filename.lower().endswith(ext) for ext in ["png", "jpg", "jpeg", "bmp", "webp", "avif"]):
            continue

        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    print("[main] Failed to download the image.")
                    return
                data = await resp.read()

        os.makedirs("images", exist_ok=True)
        local_path = os.path.join("images", attachment.filename)
        with open(local_path, "wb") as f:
            f.write(data)

        img = Image.open(io.BytesIO(data))
        avif_buffer = io.BytesIO()
        img.save(avif_buffer, format="AVIF", quality=0)
        avif_buffer.seek(0)

        filename_no_ext = os.path.splitext(attachment.filename)[0]
        avif_filename = f"{filename_no_ext}.avif"
        avif_files.append(discord.File(fp=avif_buffer, filename=avif_filename))

    if avif_files:
        await message.channel.send(content=original_text, files=avif_files)
        
        try:
            await message.delete()
            print("[main] Original message deleted")
        except discord.Forbidden:
            print("[main] Missing permissions to delete the original message")
        except discord.NotFound:
            print("[main] Original message already deleted")
