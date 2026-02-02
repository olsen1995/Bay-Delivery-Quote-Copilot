from fastapi import APIRouter, Query
from storage.memory_manager import MemoryManager
import logging
import json

router = APIRouter()
logger = logging.getLogger("lifeos")


@router.get("/get")
def get_memory(user_id: str = Query(..., min_length=1)):
    """
    Read-only memory fetch.
    Missing memory returns ok with empty {}.
    """
    mm = MemoryManager(user_id)

    try:
        memory = mm.get_all()
    except Exception:
        memory = {}

    # JSON-serialized logging for structured output
    logger.info(json.dumps({
        "event": "memory_read",
        "user_id": user_id,
        "keys": len(memory.keys())
    }))

    return {
        "status": "ok",
        "user_id": user_id,
        "memory": memory,
    }

