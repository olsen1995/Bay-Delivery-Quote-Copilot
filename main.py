import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import openai

from fastapi.openapi.utils import get_openapi

# Load environment variables
load_dotenv()

# OpenAI Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Request model
class PromptRequest(BaseModel):
    prompt: str

# Create app
app = FastAPI()


# ✅ FIX: Override OpenAPI Schema for GPT Actions
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="LifeOS Co-Pilot API",
        version="1.0.0",
        description="API for LifeOS Co-Pilot GPT Actions",
        routes=app.routes,
    )

    # ✅ REQUIRED for ChatGPT Actions
    schema["servers"] = [
        {
            "url": "https://life-os-private-practical-co-pilot.onrender.com",
            "description": "Render Production Server"
        }
    ]

    app.openapi_schema = schema
    return app.openapi_schema


# Apply override
app.openapi = custom_openapi


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root test
@app.get("/")
def read_root():
    return {"message": "LifeOS Co-Pilot API is running."}


# Main GPT endpoint
@app.post("/ask")
async def ask_openai(request: PromptRequest):
    prompt = request.prompt

    if not prompt:
        return JSONResponse(content={"error": "Prompt required"}, status_code=400)

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are the LifeOS Co-Pilot assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        message = response.choices[0].message.content

        if not message:
            return JSONResponse(content={"error": "No response returned"}, status_code=500)

        return {"response": message.strip()}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
