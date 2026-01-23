from openai import OpenAI
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def handle_fixit_mode(input_text: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're an expert developer. Help debug or fix user-submitted code."},
                {"role": "user", "content": input_text}
            ]
        )

        reply = response.choices[0].message.content

        return {
            "issue": "See AI-generated suggestion below",
            "suggestion": "This is generated based on the code you submitted.",
            "patch": reply
        }

    except Exception as e:
        return {
            "issue": "Error during processing",
            "suggestion": str(e),
            "patch": ""
        }
