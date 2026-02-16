from fastapi import FastAPI, UploadFile, File
from typing import List
from app.image_analyzer import analyze_image
from app.pricing_engine import calculate_quote

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Bay Delivery Quote Copilot API running"}


@app.post("/analyze-image")
async def analyze_uploaded_images(files: List[UploadFile] = File(...)):
    all_analyses = []

    for file in files:
        analysis = analyze_image(file)
        all_analyses.append(analysis)

    # Merge multiple image analyses (basic merge logic)
    merged_analysis = {
        "job_type": "junk_removal",
        "estimated_volume_cubic_yards": 0,
        "heavy_items": [],
        "difficulty": "easy"
    }

    for analysis in all_analyses:
        if "error" in analysis:
            return {
                "error": "Image analysis failed",
                "details": analysis
            }

        merged_analysis["estimated_volume_cubic_yards"] += analysis.get(
            "estimated_volume_cubic_yards", 0
        )

        merged_analysis["heavy_items"].extend(
            analysis.get("heavy_items", [])
        )

        # Upgrade difficulty if any image is harder
        if analysis.get("difficulty") == "hard":
            merged_analysis["difficulty"] = "hard"
        elif (
            analysis.get("difficulty") == "moderate"
            and merged_analysis["difficulty"] != "hard"
        ):
            merged_analysis["difficulty"] = "moderate"

    # Calculate final quote
    quote = calculate_quote(merged_analysis)

    return {
        "analysis": merged_analysis,
        "quote": quote
    }
