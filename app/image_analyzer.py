import base64
import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_image(file):
    contents = file.file.read()
    base64_image = base64.b64encode(contents).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a waste estimation assistant for a junk removal business. "
                    "Analyze images and return ONLY valid JSON in this format:\n\n"
                    "{\n"
                    '  "waste_type": string,\n'
                    '  "estimated_volume_cubic_yards": number,\n'
                    '  "heavy_items": [list of strings],\n'
                    '  "difficulty": "easy" | "moderate" | "hard"\n'
                    "}\n\n"
                    "Do not include explanations. Only JSON."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this image and estimate job details."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ],
            },
        ],
        max_tokens=300,
        temperature=0,
    )

    content = response.choices[0].message.content

    if content is None:
        return {
            "error": "Model returned empty response"
        }

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "error": "Model did not return valid JSON",
            "raw_response": content
        }
