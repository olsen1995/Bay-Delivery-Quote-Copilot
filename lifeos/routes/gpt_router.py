from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from lifeos.routes.canon_router import CanonRouter
from lifeos.gpt.gpt_reasoner import gpt_reason
import logging

router = APIRouter()
canon_router = CanonRouter()
logger = logging.getLogger("lifeos")

@router.get("/ask")
def gpt_ready():
    return {
        "status": "ready",
        "model": "LifeOS Co-Pilot",
        "version": "0.1.0"
    }

@router.get("/canon/query")
def gpt_query_canon(type: str):
    try:
        return canon_router.get_entries_by_type(type=type)
    except HTTPException as e:
        raise e

class ReasonRequest(BaseModel):
    intent: str
    context: Optional[str] = None
    canon_types: List[str]

@router.post("/reason")
def gpt_reason_endpoint(payload: ReasonRequest):
    canon_data: Dict[str, List[Dict[str, Any]]] = {}

    for ctype in payload.canon_types:
        try:
            canon_data[ctype] = canon_router.get_entries_by_type(type=ctype)
        except HTTPException:
            canon_data[ctype] = []

    result = gpt_reason(
        intent=payload.intent,
        context=payload.context or "",
        canon_data=canon_data
    )

    logger.info({
        "event": "gpt_reason_called",
        "intent": payload.intent,
        "types": payload.canon_types,
        "response_len": len(result["reasoning"])
    })

    return result
