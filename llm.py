import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv('GOOGLE_API_KEY')
client = genai.Client()

PROMPT_SUFFIX = "You're in a Discord server, so respond with no more than 2 sentences in a message. Don't use line breaks. Typing style is like twitter roleplays sometimes. Don't use emojis. You need to talk like Aigis from Persona 3, but towards the end of the game where shes more human. Also zy is like makoto, so treat him as such, but don't call him makoto call him zy-kun."

def generate_content_llm(message, author):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{PROMPT_SUFFIX}\n{author}'s message: {message}.",
        )
        return response.text
    except:
        return "This idiot ran out of rate limits. What an idiot. please pay us $1200 for dooooooooooooooooooooooooooooooooooooooooooookieeee~~"