import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from openai import OpenAI

# ------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------
load_dotenv()

# Ensure OpenAI key exists
api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "❌ OPENAI_API_KEY is missing.\n"
        "➡️ Set it in Render Environment or your local .env file."
    )

# ------------------------------------------------------------
# Initialize OpenAI client (NEW SDK)
# ------------------------------------------------------------
client = OpenAI(api_key=api_key)

# ------------------------------------------------------------
# Initialize FastAPI app
# ------------------------------------------------------------
app = FastAPI()

# Enable CORS (required for GPT Actions + browser calls)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# Request body schema
# ------------------------------------------------------------
class PromptRequest(BaseModel):
    prompt: Optional[str] = None  # ✅ Optional so Pylance knows it can be None


# ------------------------------------------------------------
# Root health endpoint
# ------------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "LifeOS Co-Pilot API is running."}


# ------------------------------------------------------------
# Main GPT endpoint
# ------------------------------------------------------------
@app.post("/ask")
def ask_openai(prompt_request: PromptRequest):
    # ✅ Always convert prompt safely into a real string
    prompt: str = (prompt_request.prompt or "").strip()

    # Reject empty prompts
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    try:
        # Call OpenAI chat completion
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are LifeOS Co-Pilot: calm, practical, privacy-first, "
                        "and focused on giving the user the next clear step."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=700,
        )

        # ✅ Safely extract response text
        answer: str = (response.choices[0].message.content or "").strip()

        return {"response": answer}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI API Error: {str(e)}",
        )
