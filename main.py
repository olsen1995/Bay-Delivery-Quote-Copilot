from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# ✅ LangChain v1+ Correct Imports
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import OpenAI

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI()

# Allow CORS (useful for dev/testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Static Files for Plugin Support
# -----------------------------

# Serve the .well-known folder (legacy plugin support)
app.mount(
    "/.well-known",
    StaticFiles(directory=os.path.join(os.getcwd(), "static", "well-known")),
    name="well-known",
)

# Serve openapi.json from root
@app.get("/openapi.json")
async def get_openapi():
    return FileResponse("openapi.json")


# Health check route
@app.get("/ping")
def ping():
    return {"message": "pong"}


# -----------------------------
# ✅ /ask Endpoint (Custom GPT)
# -----------------------------

# Load OpenAI key from .env
openai_api_key = os.getenv("OPENAI_API_KEY")

# ✅ Correct OpenAI initialization for LangChain v1+
llm = OpenAI(
    temperature=0.7,
    openai_api_key=openai_api_key
)

# Prompt template
template = """
You are a helpful assistant helping someone reduce overwhelm and gain emotional clarity.

User question: {prompt}

Give a thoughtful, supportive, actionable response.
"""

prompt_template = PromptTemplate(
    input_variables=["prompt"],
    template=template
)

# Chain
llm_chain = LLMChain(
    llm=llm,
    prompt=prompt_template
)


# Request + Response Models
class AskRequest(BaseModel):
    user_id: str
    prompt: str


class AskResponse(BaseModel):
    response: str


# ✅ Main GPT endpoint
@app.post("/ask", response_model=AskResponse)
async def ask_route(payload: AskRequest):
    try:
        print(f"Prompt from {payload.user_id}: {payload.prompt}")

        answer = llm_chain.run(payload.prompt)

        return AskResponse(response=answer)

    except Exception as e:
        print("Error in /ask:", e)
        return AskResponse(
            response="Sorry — something went wrong while processing your request."
        )
