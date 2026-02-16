import base64
import os
from openai import OpenAI
from fastapi import UploadFile


def analyze_image(file: UploadFile):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    client = OpenAI(api_key=api_key)

    contents = file.file.read()
    encoded_image = base64.b64encode(contents).decode("utf-8")

    prompt = """
You are a junk removal estimator assistant.

Analyze the image and return structured JSON with:

- items_detected (list)
- estimated_trailer_load (fraction between 0 and 1)
- heavy_items_count (integer)
- stairs_detected (true/false)
- access_difficulty (easy, medium, hard)
- notes (short explanation)

Only return valid JSON.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        },
                    },
                ],
            }
        ],
    )

    return response.choices[0].message.content
