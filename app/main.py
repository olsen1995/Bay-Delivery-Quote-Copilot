from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from app.quote_engine import calculate_quote
from app.image_analyzer import analyze_image
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

app = FastAPI(title="Bay Delivery Quote Copilot")


class QuoteRequest(BaseModel):
    service_type: str
    estimated_hours: float
    dump_fee_estimate: float = 0


@app.post("/ask")
def ask_quote(request: QuoteRequest):
    result = calculate_quote(
        service_type=request.service_type,
        hours=request.estimated_hours,
        dump_fee_estimate=request.dump_fee_estimate,
    )
    return result


@app.post("/analyze-image")
async def analyze_uploaded_image(file: UploadFile = File(...)):
    analysis = analyze_image(file)
    return {"analysis": analysis}
