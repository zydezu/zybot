import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor
from collections import Counter

DEFAULT_AVATAR_PATH = "media/pictures/defaultavatar.png"

def get_accent_colour(user):
    useravatarimage = Image.open(requests.get(user.avatar, stream=True).raw) if user else Image.open(DEFAULT_AVATAR_PATH)
    rgb, hex_color, color_image = get_accent_color(useravatarimage)
    return hex_color, color_image

def rgb_to_hsv(rgb):
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    diff = max_c - min_c

    if max_c == min_c:
        h = 0
    elif max_c == r:
        h = (60 * ((g - b) / diff) + 360) % 360
    elif max_c == g:
        h = (60 * ((b - r) / diff) + 120) % 360
    else:
        h = (60 * ((r - g) / diff) + 240) % 360

    s = 0 if max_c == 0 else (diff / max_c) * 100
    v = max_c * 100

    return h, s, v

def get_color_score(rgb):
    h, s, v = rgb_to_hsv(rgb)
    luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    if luminance < 30 or luminance > 230:
        return 0
    if v < 20 or v > 90:
        return 0
    if s < 15:
        return 0
    return s * (1 - abs(v - 50) / 50)

def get_accent_color(image):
    image = image.resize((50, 50)).convert('RGB')
    pixels = list(image.getdata())

    if not pixels:
        default_hex = "#bc0839"
        default_image = Image.new('RGB', (50, 50), default_hex)
        return (188, 8, 57), default_hex, default_image

    color_scores = {}
    for pixel in pixels:
        score = get_color_score(pixel)
        if score > 0:
            color_scores[pixel] = color_scores.get(pixel, 0) + score

    if not color_scores:
        default_hex = "#bc0839"
        default_image = Image.new('RGB', (50, 50), default_hex)
        return (188, 8, 57), default_hex, default_image

    most_common_color = max(color_scores, key=color_scores.get)
    hex_color = "#{:02x}{:02x}{:02x}".format(*most_common_color)
    color_image = Image.new('RGB', (50, 50), hex_color)

    return most_common_color, hex_color, color_image