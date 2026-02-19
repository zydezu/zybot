import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor
from collections import Counter

DEFAULT_AVATAR_PATH = "media/pictures/defaultavatar.png"

def get_accent_colour(user):
    useravatarimage = Image.open(requests.get(user.avatar, stream=True).raw) if user else Image.open(DEFAULT_AVATAR_PATH)
    rgb, hex_color, color_image = get_accent_color(useravatarimage)
    return hex_color, color_image

def get_luminance(rgb):
    """Calculate the perceived luminance of an RGB color."""
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b

def get_accent_color(image, min_luminance=50, max_luminance=200):
    """Get the accent color of an image, excluding very dark and very light colors."""

    # Resize the image to speed up processing
    image = image.resize((100, 100))
    
    # Convert the image to RGB if it's not already
    image = image.convert('RGB')
    
    # Get all pixels from the image
    pixels = list(image.getdata())
    
    # Filter out dark colors based on luminance
    filtered_pixels = [
        pixel for pixel in pixels 
        if min_luminance <= get_luminance(pixel) <= max_luminance
    ]
    
    if not filtered_pixels:
        default_hex = "#bc0839"
        default_image = Image.new('RGB', (50, 50), default_hex)
        return (128, 8, 57), default_hex, default_image
    
    # Find the most common color among the filtered pixels
    most_common_color = Counter(filtered_pixels).most_common(1)[0][0]
    hex_color = "#{:02x}{:02x}{:02x}".format(*most_common_color)
    color_image = Image.new('RGB', (50, 50), hex_color)
    
    return most_common_color, hex_color, color_image

print(get_accent_colour(None))