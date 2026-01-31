import json
import os
import re
from fastapi import HTTPException

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "../../storage/user_memory")

class MemoryManager:
    def __init__(self, user_id: str):
        self.user_id = self._sanitize_user_id(user_id)
        self.file_path = os.path.join(MEMORY_DIR, f"{self.user_id}.json")

    def _sanitize_user_id(self, user_id: str) -> str:
        """Allow only alphanumeric, dash, underscore for safety."""
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)
        return safe_id

    def get_all(self) -> dict:
        """Load memory from disk. Return empty dict if file not found."""
        try:
            if not os.path.exists(self.file_path):
                return {}
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail="Corrupt memory file") from e

    def set_all(self, data: dict):
        """Atomically write full memory to disk."""
        try:
            temp_path = f"{self.file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, self.file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to write memory") from e
