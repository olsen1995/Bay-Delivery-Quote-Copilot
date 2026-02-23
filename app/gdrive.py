from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession


GDRIVE_FOLDER_ID_ENV = "GDRIVE_FOLDER_ID"
GDRIVE_SA_KEY_B64_ENV = "GDRIVE_SA_KEY_B64"
GDRIVE_BACKUP_KEEP_ENV = "GDRIVE_BACKUP_KEEP"

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3"


class DriveNotConfigured(RuntimeError):
    pass


@dataclass
class DriveFile:
    file_id: str
    name: str
    mime_type: str
    web_view_link: Optional[str] = None
    size: Optional[int] = None
    created_time: Optional[str] = None


def is_configured() -> bool:
    return bool(os.getenv(GDRIVE_FOLDER_ID_ENV)) and bool(os.getenv(GDRIVE_SA_KEY_B64_ENV))


def _load_service_account_info() -> Dict[str, Any]:
    b64 = os.getenv(GDRIVE_SA_KEY_B64_ENV, "").strip()
    if not b64:
        raise DriveNotConfigured("Missing GDRIVE_SA_KEY_B64 environment variable.")
    try:
        raw = base64.b64decode(b64.encode("utf-8")).decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        raise DriveNotConfigured(f"Failed to decode GDRIVE_SA_KEY_B64: {e}")


def _session() -> AuthorizedSession:
    info = _load_service_account_info()
    creds = service_account.Credentials.from_service_account_info(info, scopes=[DRIVE_SCOPE])
    return AuthorizedSession(creds)


def _vault_root_id() -> str:
    folder_id = os.getenv(GDRIVE_FOLDER_ID_ENV, "").strip()
    if not folder_id:
        raise DriveNotConfigured("Missing GDRIVE_FOLDER_ID environment variable.")
    return folder_id


def backup_keep_count() -> int:
    raw = os.getenv(GDRIVE_BACKUP_KEEP_ENV, "").strip()
    if not raw:
        return 50
    try:
        return max(5, int(raw))
    except Exception:
        return 50


def ensure_folder(name: str, parent_id: str) -> DriveFile:
    sess = _session()

    safe_name = name.replace("'", "\\'")
    q = (
        "mimeType='application/vnd.google-apps.folder' and "
        f"name='{safe_name}' and "
        f"'{parent_id}' in parents and trashed=false"
    )

    r = sess.get(
        f"{DRIVE_API}/files",
        params={"q": q, "fields": "files(id,name,mimeType,webViewLink,createdTime)"},
        timeout=30,
    )
    r.raise_for_status()
    files = r.json().get("files", [])
    if files:
        f0 = files[0]
        return DriveFile(
            file_id=f0["id"],
            name=f0.get("name", name),
            mime_type=f0.get("mimeType", ""),
            web_view_link=f0.get("webViewLink"),
            created_time=f0.get("createdTime"),
        )

    payload = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    r2 = sess.post(
        f"{DRIVE_API}/files",
        json=payload,
        params={"fields": "id,name,mimeType,webViewLink,createdTime"},
        timeout=30,
    )
    r2.raise_for_status()
    f = r2.json()
    return DriveFile(
        file_id=f["id"],
        name=f.get("name", name),
        mime_type=f.get("mimeType", ""),
        web_view_link=f.get("webViewLink"),
        created_time=f.get("createdTime"),
    )


def ensure_vault_subfolders() -> Dict[str, str]:
    root = _vault_root_id()
    backups = ensure_folder("db_backups", root)
    uploads = ensure_folder("uploads", root)
    return {"root": root, "db_backups": backups.file_id, "uploads": uploads.file_id}


def upload_bytes(*, parent_id: str, filename: str, mime_type: str, content: bytes) -> DriveFile:
    sess = _session()

    metadata = {"name": filename, "parents": [parent_id]}
    files = {
        "metadata": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
        "file": (filename, content, mime_type),
    }

    r = sess.post(
        f"{DRIVE_UPLOAD}/files",
        params={"uploadType": "multipart", "fields": "id,name,mimeType,webViewLink,size,createdTime"},
        files=files,
        timeout=60,
    )
    r.raise_for_status()
    f = r.json()
    return DriveFile(
        file_id=f["id"],
        name=f.get("name", filename),
        mime_type=f.get("mimeType", mime_type),
        web_view_link=f.get("webViewLink"),
        size=int(f["size"]) if f.get("size") is not None else None,
        created_time=f.get("createdTime"),
    )


def list_files(parent_id: str, limit: int = 20) -> List[DriveFile]:
    sess = _session()
    q = f"'{parent_id}' in parents and trashed=false"
    r = sess.get(
        f"{DRIVE_API}/files",
        params={
            "q": q,
            "pageSize": int(limit),
            "orderBy": "createdTime desc",
            "fields": "files(id,name,mimeType,webViewLink,size,createdTime)",
        },
        timeout=30,
    )
    r.raise_for_status()

    out: List[DriveFile] = []
    for f in r.json().get("files", []):
        out.append(
            DriveFile(
                file_id=f["id"],
                name=f.get("name", ""),
                mime_type=f.get("mimeType", ""),
                web_view_link=f.get("webViewLink"),
                size=int(f["size"]) if f.get("size") is not None else None,
                created_time=f.get("createdTime"),
            )
        )
    return out


def download_file(file_id: str) -> bytes:
    sess = _session()
    r = sess.get(f"{DRIVE_API}/files/{file_id}", params={"alt": "media"}, timeout=60)
    r.raise_for_status()
    return r.content


def delete_file(file_id: str) -> None:
    sess = _session()
    r = sess.delete(f"{DRIVE_API}/files/{file_id}", timeout=30)
    if r.status_code not in (204, 200):
        r.raise_for_status()