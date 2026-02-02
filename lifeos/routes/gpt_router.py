from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import logging
import json
import os

from routes.canon_router import CanonRouter
from gpt.gpt_summarizer import (
    summarize_entity,
    llm_summarize_entity
)
from gpt.summary_validator import validate_summary

logger = logging.getLogger("lifeos")
router = APIRouter()
canon = CanonRouter()

class CanonQueryRequest(BaseModel):
    type: str

class CanonSearchRequest(BaseModel):
    filters: Optional[Dict[str, str]] = None

class CanonSummarizeRequest(BaseModel):
    type: str
    name: str
    use_llm: Optional[bool] = False

@router.post("/canon/query")
async def query_canon(request: CanonQueryRequest):
    entries = canon.get_entries_by_type(request.type)
    logger.info(json.dumps({
        "event": "canon_query",
        "type": request.type,
        "results": len(entries)
    }))
    return {"status": "ok", "results": entries}

@router.post("/canon/search")
async def search_canon(request: CanonSearchRequest):
    filters = request.filters or {}
    allowed_keys = {"type", "name", "version"}
    if any(k not in allowed_keys for k in filters):
        raise HTTPException(status_code=400, detail="Invalid filter keys")

    entries = canon.get_all_entries()
    results = [e for e in entries if all(e.get(k) == v for k, v in filters.items())]

    logger.info(json.dumps({
        "event": "canon_search",
        "filter_keys": list(filters.keys()),
        "results": len(results)
    }))
    return {"status": "ok", "results": results}

@router.post("/canon/summarize")
async def summarize_canon(request: CanonSummarizeRequest):
    entries = canon.get_entries_by_type(request.type)
    entity = next((e for e in entries if e.get("name") == request.name), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Load full entity content
    try:
        full_entity = canon.get_file_by_path(entity["path"])
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to load Canon file")

    # Decide summary source
    use_llm = bool(request.use_llm) and os.getenv("LLM_SUMMARIES_ENABLED") == "true"
    try:
        if use_llm:
            summary = llm_summarize_entity(full_entity)
        else:
            summary = summarize_entity(full_entity)
        validate_summary(summary, full_entity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(json.dumps({
        "event": "canon_summary_validated",
        "type": request.type,
        "name": request.name,
        "summary_length": len(summary)
    }))
    return {"status": "ok", "summary": summary}

