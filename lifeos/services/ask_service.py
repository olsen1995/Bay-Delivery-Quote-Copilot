from __future__ import annotations

from typing import Any, Dict

from storage.memory_manager import MemoryManager
from services.mode_tag_service import detect_mode  # ✅ New internal import


def handle_ask(message: str, user_id: str) -> Dict[str, Any]:
    """
    Service-layer handler for /ask.

    IMPORTANT CONTRACT:
    - Keep response shape identical to existing route behavior.
    - Do not introduce new required fields without updating OpenAPI.
    """

    _mode = detect_mode(message)  # ✅ Internal-only usage

    mm = MemoryManager(user_id)
    memory = mm.get_all()

    # Preserve current minimal behavior (echo-style summary).
    return {"summary": f"You said: {message}", "user_id": user_id, "memory": memory}
