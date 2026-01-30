import os
import json
from typing import List, Dict
from pathlib import Path
from datetime import datetime, timezone

MEMORY_DIR = Path("storage/user_memory")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

class MemoryManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.file_path = MEMORY_DIR / f"{user_id}.json"

    def _load(self) -> List[Dict]:
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self, data: List[Dict]):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_memory(self, text: str):
        memory = {"text": text, "timestamp": self._now()}
        data = self._load()
        data.append(memory)
        self._save(data)

    def get_all(self) -> List[Dict]:
        return self._load()

    def delete_all(self):
        self._save([])

    def _now(self):
        return datetime.now(timezone.utc).isoformat() + "Z"
