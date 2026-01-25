import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Initialize OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define request model
class PromptRequest(BaseModel):
    prompt: str

# Create FastAPI app
app = FastAPI()

# Enable CORS for all origins (you can restrict this for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "LifeOS Co-Pilot API is running."}

# Chat endpoint
@app.post("/ask")
async def ask_openai(request: PromptRequest):
    prompt = request.prompt

    if not prompt:
        return JSONResponse(content={"error": "Prompt is required"}, status_code=400)

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        message = response.choices[0].message.content if response.choices else None

        if not message:
            return JSONResponse(content={"error": "No response from OpenAI"}, status_code=500)

        return {"response": message.strip()}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
