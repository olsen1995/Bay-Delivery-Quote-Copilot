import json
import os
from fastapi import APIRouter, HTTPException

CANON_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "..", "canon", "Canon_Manifest.json")


class CanonRouter:
    def __init__(self):
        self.router = APIRouter()
        self.router.get("/file")(self.get_file_by_path)
        self.router.get("/types")(self.get_types)

    def get_manifest(self):
        with open(CANON_MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_entries_by_type(self, type: str):
        return [
            entry for entry in self.get_manifest().get("entries", [])
            if entry["type"] == type
        ]

    def get_all_entries(self):
        return self.get_manifest().get("entries", [])

    def get_file_by_path(self, path: str):
        entry = next((e for e in self.get_manifest().get("entries", []) if e["path"] == path), None)
        if not entry:
            raise HTTPException(status_code=404, detail="File not found")

        full_path = os.path.join(os.path.dirname(CANON_MANIFEST_PATH), path)
        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="Path invalid or file missing")

        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_types(self):
        return list(set(entry["type"] for entry in self.get_manifest().get("entries", [])))
