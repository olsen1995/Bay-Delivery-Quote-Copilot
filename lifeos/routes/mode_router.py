from fastapi import APIRouter, Form, Query, HTTPException
from pydantic import BaseModel
from typing import Dict
from storage.memory_manager import MemoryManager
from services.ask_service import handle_ask
from services.memory_service import write_memory, read_memory, delete_memory  # ✅ NEW
import os


class MemoryWriteRequest(BaseModel):
    user_id: str
    memory: Dict[str, object]


class ModeRouter:
    def __init__(self):
        self.router = APIRouter()
        self.router.add_api_route("/ask", self.ask_handler, methods=["POST"])
        self.router.add_api_route("/ask", self.ask_handler_get, methods=["GET"])
        self.router.add_api_route("/memory", self.memory_write_handler, methods=["POST"])
        self.router.add_api_route("/memory", self.memory_read_handler, methods=["GET"])
        self.router.add_api_route("/memory", self.memory_delete_handler, methods=["DELETE"])

    def ask_handler(self, message: str = Form(...), user_id: str = Form(...)):
        return handle_ask(message=message, user_id=user_id)

    def ask_handler_get(self, message: str = Query(...), user_id: str = Query(...)):
        return handle_ask(message=message, user_id=user_id)

    def memory_write_handler(self, payload: MemoryWriteRequest):
        return write_memory(user_id=payload.user_id, memory=payload.memory)

    def memory_read_handler(self, user_id: str = Query(...)):
        return read_memory(user_id=user_id)

    def memory_delete_handler(self, user_id: str = Query(...)):
        try:
            return delete_memory(user_id=user_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to delete memory") from e
