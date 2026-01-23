import os
from typing import Dict
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client (SDK v1+)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def handle_lifecoach_mode(user_input: str) -> Dict[str, str]:
    """
    GPT-powered LifeCoach mode.
    Provides empathetic, motivating, and practical guidance.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a compassionate and practical life coach. "
                        "Validate the user's feelings, respond with empathy, "
                        "and provide clear, actionable guidance in a calm, supportive tone."
                    ),
                },
                {"role": "user", "content": user_input},
            ],
            max_tokens=500,
            temperature=0.7,
        )

        content = response.choices[0].message.content or ""

        return {
            "response": content.strip()
        }

    except Exception as e:
        return {
            "error": f"LifeCoach failed: {str(e)}"
        }
