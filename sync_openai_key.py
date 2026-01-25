import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load from .env file

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([RENDER_API_KEY, RENDER_SERVICE_ID, OPENAI_API_KEY]):
    raise SystemExit("❌ Missing one or more required environment variables.")

url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars"

headers = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

payload = {
    "envVars": [
        {
            "key": "OPENAI_API_KEY",
            "value": OPENAI_API_KEY
        }
    ]
}

response = requests.put(url, headers=headers, json=payload)

if response.status_code == 200:
    print("✅ OPENAI_API_KEY updated successfully on Render.")
else:
    print("❌ Failed to update. Response:")
    print(response.status_code, response.text)
