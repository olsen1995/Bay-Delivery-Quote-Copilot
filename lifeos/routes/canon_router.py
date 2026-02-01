import os
import json
import logging
import hashlib
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

logger = logging.getLogger("lifeos")

CANON_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "canon")
)
CANON_MANIFEST_PATH = os.path.join(CANON_ROOT, "Canon_Manifest.json")


class CanonRouter:
    def __init__(self):
        self.router = APIRouter()

        # Routes are relative to mount point (/canon)
        self.router.get("/types")(self.get_canon_types)
        self.router.get("/file")(self.get_file)
        self.router.get("/snapshot")(self.get_snapshot)
        self.router.get("/snapshot/digest")(self.get_snapshot_digest)

    def get_manifest(self) -> Dict[str, Any]:
        with open(CANON_MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_file_by_path(self, path: str) -> Dict[str, Any]:
        full_path = os.path.abspath(os.path.join(CANON_ROOT, path))

        # Enforce Canon root containment (no traversal)
        if not full_path.startswith(CANON_ROOT):
            raise HTTPException(status_code=403, detail="Access denied")

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"Canon file not found: {path}")

        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_entries_by_type(self, type: str) -> List[Dict[str, Any]]:
        return [
            entry
            for entry in self.get_manifest().get("entries", [])
            if entry.get("type") == type
        ]

    def get_all_entries(self) -> List[Dict[str, Any]]:
        return self.get_manifest().get("entries", [])

    def _build_snapshot_entries(self) -> List[Dict[str, Any]]:
        manifest = self.get_manifest()
        entries: List[Dict[str, Any]] = []

        for entry in manifest.get("entries", []):
            content = self.get_file_by_path(entry["path"])
            entries.append({**entry, "content": content})

        return entries

    async def get_canon_types(self):
        manifest = self.get_manifest()
        types = sorted({e["type"] for e in manifest.get("entries", [])})
        return {"status": "ok", "types": types}

    async def get_file(self, type: str, name: str):
        entries = self.get_entries_by_type(type)
        match = next((e for e in entries if e.get("name") == name), None)

        if match is None:
            raise HTTPException(status_code=404, detail="Entity not found")

        try:
            entity = self.get_file_by_path(match["path"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        return {"status": "ok", "entity": entity}

    async def get_snapshot(self):
        try:
            entries = self._build_snapshot_entries()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Snapshot error: {str(e)}")

        logger.info(
            json.dumps(
                {
                    "event": "canon_snapshot_requested",
                    "entry_count": len(entries),
                }
            )
        )

        return {"status": "ok", "entries": entries}

    async def get_snapshot_digest(self):
        try:
            entries = self._build_snapshot_entries()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Snapshot error: {str(e)}")

        canonical_json = json.dumps(
            entries, sort_keys=True, separators=(",", ":")
        )
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        logger.info(
            json.dumps(
                {
                    "event": "canon_snapshot_digest_computed",
                    "entry_count": len(entries),
                    "digest_length": 64,
                }
            )
        )

        return {"status": "ok", "digest": digest}
