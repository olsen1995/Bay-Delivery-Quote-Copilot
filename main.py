import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI, OpenAIError

# ------------------------------------------------------------
# Load environment variables from .env (LOCAL ONLY)
# Render ignores .env — you must set env vars in Render dashboard
# ------------------------------------------------------------
load_dotenv()

# ------------------------------------------------------------
# Safely load API key (prevents strip() None errors)
# ------------------------------------------------------------
api_key = os.getenv("OPENAI_API_KEY") or ""

if not api_key.strip():
    raise RuntimeError(
        "❌ OPENAI_API_KEY is missing.\n"
        "➡️ Set it in Render → Environment tab.\n"
        "➡️ Or add it to your local .env file."
    )

# Initialize OpenAI client
client = OpenAI(api_key=api_key.strip())

# ------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------
app = FastAPI()


# ------------------------------------------------------------
# Request/Response Models
# ------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


# ------------------------------------------------------------
# Health Check (Render uses this)
# ------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ------------------------------------------------------------
# Root Route
# ------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "LifeOS CoPilot is running!"}


# ------------------------------------------------------------
# Chat Endpoint
# ------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are LifeOS, a helpful AI co-pilot."},
                {"role": "user", "content": request.message},
            ],
        )

        # Safe: content might be None
        content = response.choices[0].message.content
        reply = content.strip() if content else "[No response returned]"

        return ChatResponse(response=reply)

    except OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
