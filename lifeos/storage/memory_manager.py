import json
from typing import List, Dict
from pathlib import Path
from datetime import datetime, timezone

# ✅ Storage directory for user memory
MEMORY_DIR = Path("storage/user_memory")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class MemoryManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.file_path = MEMORY_DIR / f"{user_id}.json"

    # ----------------------------
    # Internal Helpers
    # ----------------------------

    def _load(self) -> List[Dict]:
        """Load memory list from disk."""
        if not self.file_path.exists():
            return []

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self, data: List[Dict]):
        """Save memory list to disk."""
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _now(self) -> str:
        """Return timezone-aware UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    # ----------------------------
    # Public API Methods
    # ----------------------------

    def add_memory(self, text: str):
        """Add a memory entry."""
        memory = {"text": text, "timestamp": self._now()}
        data = self._load()
        data.append(memory)
        self._save(data)

    def get_memory(self) -> List[Dict]:
        """Return all stored memories (used by /memory GET)."""
        return self._load()

    def clear_memory(self):
        """Delete all stored memories (used by /memory POST)."""
        self._save([])
