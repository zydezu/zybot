import os, sys
from datetime import datetime
from yt_dlp import YoutubeDL

class bcolors:
    OKBLUE = '\033[94m'
    WARNING = '\033[93m'
    LINE = '\033[90m'
    ENDC = '\033[0m'

VIDEO_LIST = "listofvideos.txt"

def set_terminal_title(title):
    if os.name == 'nt':  # Windows
        os.system(f"title {title}")
    else:  # Unix/Linux/Mac
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

def startvideodownload(url=None, extraInfo=""):
    link = url
    if url == None:
        set_terminal_title("YouTube Page Generator")
        print(f"{bcolors.OKBLUE}Enter the link of the {bcolors.WARNING}video{bcolors.OKBLUE} to generate a page for...{bcolors.ENDC}")
        print(f"{bcolors.LINE}---------------------------------------")
        link = input(f"{bcolors.WARNING}Link {bcolors.ENDC}> {bcolors.WARNING}")
        print(f"{bcolors.LINE}---------------------------------------{bcolors.WARNING}")
        print(f"{bcolors.OKBLUE}Downloading video...")
        print(f"{bcolors.LINE}---------------------------------------{bcolors.ENDC}")

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
            'default': f'generated/{videoid}/videos/video.%(ext)s',
            'infojson': f'generated/{videoid}/videos/video',
            'thumbnail': f'generated/{videoid}/videos/video.%(ext)s',
        },
    }

    set_terminal_title(f"Downloading {videotitle} [{videoid}] {extraInfo}...")
    while True:
        try:
            with YoutubeDL(ytdlp_opts) as ytdlp:
                ytdlp.download([link])
            break
        except:
                print(f"{bcolors.LINE}---------------------------------------{bcolors.ENDC}")
                print(f"{bcolors.WARNING}Error! Retrying download...")
                print(f"{bcolors.LINE}---------------------------------------{bcolors.ENDC}")

    print(f"{bcolors.LINE}---------------------------------------{bcolors.ENDC}")
    print(f"{bcolors.OKBLUE}Download done! Generating page...")
    print(f"{bcolors.LINE}---------------------------------------{bcolors.ENDC}")
    set_terminal_title("Generating page...")

    def basestring(lst):
        if not lst:
            return ""
        common_sub = lst[0]
        for string in lst[1:]:
            common_sub = ''.join(c1 for c1, c2 in zip(common_sub, string) if c1 == c2)
            if not common_sub:
                break
        return common_sub

    fileslist = os.listdir('generated/{0}/videos'.format(videoid))
    base = basestring(fileslist)[:-1]
    filename = base + '.mp4'
    imagepath = base + '.webp'

    with open('template.txt', 'r', encoding="utf-8") as file:
        templatefile = file.read()
        outputfile = templatefile.format(videotitle=videotitle, filename=filename, icon=imagepath)
        with open("generated/{0}/index.html".format(videoid), "w", encoding="utf-8") as writefile:
            writefile.writelines(outputfile)

    # Append the new line
    with open(VIDEO_LIST, 'a', encoding="utf-8") as file:
        file.write("""\t{0} | <a href="generated/{1}/">generated/{1}/</a> | {2}<br/>\n""".format(
            videotitle, videoid, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # Read all lines
    with open(VIDEO_LIST, 'r', encoding="utf-8") as file:
        allLines = file.readlines()

    # Remove duplicates while preserving order
    seen = set()
    uniqueLines = []
    for line in allLines:
        # Extract title and video ID (ignore timestamp)
        parts = line.strip().split('|')
        if len(parts) >= 2:
            title = parts[0].strip()
            video_link = parts[1].strip()
            key = (title, video_link)
            if key not in seen:
                seen.add(key)
                uniqueLines.append(line)

    # Overwrite the file with deduplicated lines
    with open(VIDEO_LIST, 'w', encoding="utf-8") as file:
        file.writelines(uniqueLines)

    with open('index.html', 'w', encoding="utf-8") as file:
        file.writelines("""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Archived Videos</title>
        <link rel="stylesheet" href="style.css">
        <style>body{{margin:15px;}}</style>
    </head>
    <body>
    {0}
    </body>
    </html>""".format("".join(uniqueLines)))

    print("File written to index.html!")

    return videoid