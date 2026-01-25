from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
import os

# Load environment variables locally (.env) – Render already injects them
load_dotenv()

# Get the OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("❌ OPENAI_API_KEY is missing. Set it in .env or Render.")

# Initialize OpenAI client (v2+ style)
client = OpenAI(api_key=api_key)

# Setup FastAPI app
app = FastAPI()

# Optional: allow frontend connections (adjust origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check route
@app.get("/healthz")
def health_check():
    return {"status": "ok"}

# Request model
class PromptRequest(BaseModel):
    prompt: str

# POST /ask endpoint — GPT chat
@app.post("/ask")
def ask_gpt(req: PromptRequest):
    try:
        chat_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": req.prompt}
            ]
        )
        return {"response": chat_response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}
