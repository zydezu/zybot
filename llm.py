import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv('GOOGLE_API_KEY')
client = genai.Client()

PROMPT_SUFFIX = "Type like you're in a Discord server, so only type a few sentences. Typing style is like twitter aswell. Don't use emojis. Sometimes type slightly broken (unique typing-quirk). Sound (androgynous) boyish."

def generate_content_llm(message):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{message} {PROMPT_SUFFIX}",
        )
        return response.text
    except:
        return "This idiot ran out of rate limits. What an idiot. please pay us $1200 for dooooooooooooooooooooooooooooooooooooooooooookieeee~~"