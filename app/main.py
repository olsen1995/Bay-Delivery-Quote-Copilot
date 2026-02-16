from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List
from app.quote_engine import calculate_quote
from app.image_analyzer import analyze_image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Bay Delivery Quote Copilot")


# ------------------------
# Quote Engine Endpoint
# ------------------------

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


# ------------------------
# Image Analysis Endpoint (Multi-Image Support)
# ------------------------

@app.post("/analyze-image")
async def analyze_uploaded_images(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        analysis = analyze_image(file)
        results.append({
            "filename": file.filename,
            "analysis": analysis
        })

    return {"analyses": results}
