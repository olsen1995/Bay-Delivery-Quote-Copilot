from fastapi import APIRouter, Form, Query, HTTPException
from pydantic import BaseModel
from typing import Dict
from storage.memory_manager import MemoryManager
import os


class MemoryWriteRequest(BaseModel):
    user_id: str
    memory: Dict[str, object]


class ModeRouter:
    def __init__(self):
        self.router = APIRouter()
        self.router.add_api_route("/ask", self.ask_handler, methods=["POST"])
        self.router.add_api_route("/memory", self.memory_write_handler, methods=["POST"])
        self.router.add_api_route("/memory", self.memory_read_handler, methods=["GET"])
        self.router.add_api_route("/memory", self.memory_delete_handler, methods=["DELETE"])

    def ask_handler(self, message: str = Form(...), user_id: str = Form(...)):
        mm = MemoryManager(user_id)
        memory = mm.get_all()
        return {
            "summary": f"You said: {message}",
            "user_id": user_id,
            "memory": memory
        }

    def memory_write_handler(self, payload: MemoryWriteRequest):
        mm = MemoryManager(payload.user_id)
        mm.set_all(payload.memory)
        return {"ok": True, "written": len(payload.memory.keys())}

    def memory_read_handler(self, user_id: str = Query(...)):
        mm = MemoryManager(user_id)
        return mm.get_all()

    def memory_delete_handler(self, user_id: str = Query(...)):
        mm = MemoryManager(user_id)

        # ✅ Idempotent behavior: missing file is not an error
        if not os.path.exists(mm.file_path):
            return {"ok": True, "deleted": False}

        # ✅ Full file deletion only
        try:
            os.remove(mm.file_path)
            return {"ok": True, "deleted": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to delete memory") from e

