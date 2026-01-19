import os
from datetime import datetime
from yt_dlp import YoutubeDL

class bcolors:
    OKBLUE = '\033[94m'
    WARNING = '\033[93m'
    LINE = '\033[90m'
    ENDC = '\033[0m'

DOWNLOAD_DIR = "videos/downloads"
TEMPLATE = "videos/template.txt"
VIDEO_LIST = "videos/listofvideos.txt"

def get_common_prefix(strings: list[str]) -> str:
    if not strings:
        return ""
    prefix = strings[0]
    for s in strings[1:]:
        prefix = ''.join(c1 for c1, c2 in zip(prefix, s) if c1 == c2)
        if not prefix:
            break
    return prefix

def remove_duplicates_from_list(file_path: str):
    if not os.path.exists(file_path):
        return []

    seen = set()
    unique_lines = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 2:
                continue
            key = (parts[0].strip(), parts[1].strip())
            if key not in seen:
                seen.add(key)
                unique_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(unique_lines)

    return unique_lines

def startvideodownload(url=None, extraInfo=""):
    link = url

    ytdlp_opts = {
        "skip_download": True,
        'quiet': True
    }

    with YoutubeDL(ytdlp_opts) as ytdlp:
        info_dict = ytdlp.extract_info(link, download=False)
        videoid = info_dict.get('id', None)
        videotitle = info_dict.get('title', None)

    ytdlp_opts = {
        'format': 'bestvideo+bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegVideoRemuxer',
            'preferedformat': 'mp4',
        }],
        'restrictfilenames': True,
        'addmetadata': True,
        'subtitlesformat': 'best',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'writeinfojson': True,
        'getcomments': True,
        'writethumbnail': True,
        'outtmpl': {
            'default': f'{DOWNLOAD_DIR}/{videoid}/videos/video.%(ext)s',
            'infojson': f'{DOWNLOAD_DIR}/{videoid}/videos/video',
            'thumbnail': f'{DOWNLOAD_DIR}/{videoid}/videos/video.%(ext)s',
        },
    }

    # Spend infinite attempts at downloading the video
    while True:
        try:
            with YoutubeDL(ytdlp_opts) as ytdlp:
                ytdlp.download([link])
            break
        except Exception as e:
            print(f"[downloadvideo] {e}. Retrying download...")

    print(f"[downloadvideo] Download done! Generating HTML page...")

    # Generate index.html for the video
    files = os.listdir(f"{DOWNLOAD_DIR}/{videoid}/videos")
    base = get_common_prefix(files)[:-1]
    filename = base + '.mp4'
    imagepath = base + '.webp'

    with open(TEMPLATE, 'r', encoding='utf-8') as f:
        template_content = f.read()
    with open(os.path.join(DOWNLOAD_DIR, videoid, "index.html"), 'w', encoding='utf-8') as f:
        f.write(template_content.format(videotitle=videotitle, filename=filename, icon=imagepath))

    # Add to video list and remove duplicates
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(VIDEO_LIST, 'a', encoding='utf-8') as f:
        f.write(f"\t{videotitle} | <a href=\"videos/downloads/{videoid}/\">videos/downloads/{videoid}/</a> | {timestamp}<br/>\n")

    unique_lines = remove_duplicates_from_list(VIDEO_LIST)

    # Update main index.html
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archived Videos</title>
<link rel="stylesheet" href="style.css">
<style>body{{margin:15px;}}</style>
</head>
<body>
{"".join(unique_lines)}
</body>
</html>""")

    print("[downloadvideo] Finished writing to index.html!")

    return videoid