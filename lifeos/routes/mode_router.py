from fastapi import APIRouter, Form, Query
from pydantic import BaseModel
from typing import Dict
from lifeos.storage.memory_manager import MemoryManager

class MemoryWriteRequest(BaseModel):
    user_id: str
    memory: Dict[str, object]

class ModeRouter:
    def __init__(self):
        self.router = APIRouter()
        self.router.add_api_route("/ask", self.ask_handler, methods=["POST"])
        self.router.add_api_route("/memory", self.memory_write_handler, methods=["POST"])
        self.router.add_api_route("/memory", self.memory_read_handler, methods=["GET"])

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
