from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List
from app.image_analyzer import analyze_image
from app.pricing_engine import calculate_quote

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Bay Delivery Quote Copilot API running"}


# -----------------------------
# AI Image Endpoint
# -----------------------------
@app.post("/analyze-image")
async def analyze_uploaded_images(files: List[UploadFile] = File(...)):
    all_analyses = []

    for file in files:
        analysis = analyze_image(file)
        all_analyses.append(analysis)

    merged_analysis = {
        "job_type": "junk_removal",
        "estimated_volume_cubic_yards": 0,
        "heavy_items": [],
        "difficulty": "easy"
    }

    for analysis in all_analyses:
        if "error" in analysis:
            return {
                "error": "AI analysis unavailable. Use /manual-quote instead.",
                "details": analysis
            }

        merged_analysis["estimated_volume_cubic_yards"] += analysis.get(
            "estimated_volume_cubic_yards", 0
        )

        merged_analysis["heavy_items"].extend(
            analysis.get("heavy_items", [])
        )

        if analysis.get("difficulty") == "hard":
            merged_analysis["difficulty"] = "hard"
        elif (
            analysis.get("difficulty") == "moderate"
            and merged_analysis["difficulty"] != "hard"
        ):
            merged_analysis["difficulty"] = "moderate"

    quote = calculate_quote(merged_analysis)

    return {
        "analysis": merged_analysis,
        "quote": quote
    }


# -----------------------------
# Manual Quote Endpoint
# -----------------------------
class ManualQuoteRequest(BaseModel):
    job_type: str
    estimated_volume_cubic_yards: float = 0
    heavy_items: List[str] = []
    difficulty: str = "easy"
    estimated_hours: float | None = None


@app.post("/manual-quote")
def manual_quote(data: ManualQuoteRequest):
    analysis = {
        "job_type": data.job_type,
        "estimated_volume_cubic_yards": data.estimated_volume_cubic_yards,
        "heavy_items": data.heavy_items,
        "difficulty": data.difficulty,
        "estimated_hours": data.estimated_hours
    }

    quote = calculate_quote(analysis)

    return {
        "analysis": analysis,
        "quote": quote
    }
