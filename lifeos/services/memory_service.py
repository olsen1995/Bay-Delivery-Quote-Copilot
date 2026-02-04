from __future__ import annotations

from typing import Any, Dict

from storage.memory_manager import MemoryManager


def write_memory(user_id: str, memory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Service-layer handler for POST /memory.

    IMPORTANT CONTRACT:
    - Response shape must match current route behavior exactly.
    - If mode_router.py currently returns different keys, update this function to match.
    """
    mm = MemoryManager(user_id)
    mm.set_all(memory)
    return {"ok": True, "written": len(memory.keys())}


def read_memory(user_id: str) -> Dict[str, Any]:
    """
    Service-layer handler for GET /memory.
    IMPORTANT CONTRACT: response shape must match current route behavior.
    """
    mm = MemoryManager(user_id)
    return mm.get_all()


def delete_memory(user_id: str) -> Dict[str, Any]:
    """
    Service-layer handler for DELETE /memory.

    IMPORTANT CONTRACT:
    - Response shape must match current route behavior exactly.
    - Preserve idempotent behavior (missing file is not an error) if current route does so.
    """
    mm = MemoryManager(user_id)

    try:
        import os

        if not os.path.exists(mm.file_path):
            return {"ok": True, "deleted": False}

        os.remove(mm.file_path)
        return {"ok": True, "deleted": True}
    except Exception:
        raise
