import os
import json
from fastapi import APIRouter, HTTPException
from typing import List, Dict
import logging

CANON_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "canon"))
CANON_MANIFEST_PATH = os.path.join(CANON_ROOT, "Canon_Manifest.json")

logger = logging.getLogger("lifeos")


class CanonRouter:
    def __init__(self):
        self.router = APIRouter()
        self.router.get("/types")(self.get_types)
        self.router.get("/file")(self.get_file)
        self.router.get("/snapshot")(self.get_snapshot)

    def get_manifest(self) -> Dict:
        with open(CANON_MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_file_by_path(self, path: str) -> Dict:
        full_path = os.path.abspath(os.path.join(CANON_ROOT, path))
        if not full_path.startswith(CANON_ROOT):
            raise HTTPException(status_code=403, detail="Access denied")
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    def get_entries_by_type(self, type: str) -> List[Dict]:
        return [
            entry for entry in self.get_manifest().get("entries", [])
            if entry.get("type") == type
        ]

    def get_all_entries(self) -> List[Dict]:
        return self.get_manifest().get("entries", [])

    async def get_types(self):
        try:
            return {
                "status": "ok",
                "types": list(set(e["type"] for e in self.get_manifest().get("entries", []))),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_file(self, type: str, name: str):
        entries = self.get_entries_by_type(type)
        for entry in entries:
            if entry.get("name") == name:
                return {"status": "ok", "entity": self.get_file_by_path(entry["path"])}
        raise HTTPException(status_code=404, detail="Entity not found")

    async def get_snapshot(self):
        manifest = self.get_manifest()
        result = []

        for entry in manifest.get("entries", []):
            try:
                content = self.get_file_by_path(entry["path"])
                result.append(
                    {
                        "name": entry["name"],
                        "type": entry["type"],
                        "version": entry["version"],
                        "description": entry["description"],
                        "content": content,
                    }
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to load {entry['name']}: {str(e)}"
                )

        logger.info(
            json.dumps(
                {
                    "event": "canon_snapshot_requested",
                    "entry_count": len(result),
                }
            )
        )

        return {"status": "ok", "entries": result}
