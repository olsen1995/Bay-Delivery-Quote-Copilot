from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os

from openai import OpenAI
from routes import healthz

# Create OpenAI client using your API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# Health check endpoint
app.include_router(healthz.router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "LifeOS CoPilot is running!"}


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")

    if not user_message:
        return {"error": "No message provided"}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are LifeOS, a helpful AI co-pilot."},
                {"role": "user", "content": user_message},
            ],
        )

        return {"response": response.choices[0].message.content}

    except Exception as e:
        return {"error": str(e)}
