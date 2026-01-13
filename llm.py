import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv('GOOGLE_API_KEY')
client = genai.Client()

models = ["gemini-3-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemma-3-27b-it", "gemma-3-12b-it", "gemma-3-4b-it", "gemma-3-1b-it"]

PROMPT_SUFFIX = "You're in a Discord server, so respond with no more than 2 sentences in a message. Don't use line breaks. Typing style is like twitter roleplays sometimes. Don't use emojis. You need to talk like Aigis from Persona 3, but towards the end of the game where shes more human. Also zy is like makoto, so treat him as such, but don't call him makoto call him zy-kun. dont use proper grammar or capital letters."

def generate_content_llm(message, author, conversation_context):
    prompt = f"{PROMPT_SUFFIX}\n{author}'s message: {message}. The conversation so far: {conversation_context[:10].join("\n")}"

    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            if response and getattr(response, "text", None):
                return response.text
        except Exception as e:
            continue  # try next model

    return (
        "this idiot ran out of rate limits. what an idiot. "
        "please pay us $1200 for dooooooooooooooooooooooooooooooooooooooooooookieeee~~"
    )