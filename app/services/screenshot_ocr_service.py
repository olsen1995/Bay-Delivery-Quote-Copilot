from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TypedDict

OCR_PREVIEW_MAX_CHARS = 160
OCR_TEXT_MAX_CHARS = 2000
OCR_TIMEOUT_SECONDS = 12


class AttachmentOCRResult(TypedDict):
    status: str
    text: str
    preview: str
    warning: str | None


def _normalize_text(value: str | None, *, max_chars: int) -> str:
    if not value:
        return ""
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"


def _build_result(*, status: str, text: str = "", warning: str | None = None) -> AttachmentOCRResult:
    normalized_text = _normalize_text(text, max_chars=OCR_TEXT_MAX_CHARS)
    return {
        "status": status,
        "text": normalized_text,
        "preview": _normalize_text(normalized_text, max_chars=OCR_PREVIEW_MAX_CHARS),
        "warning": warning,
    }


def extract_attachment_ocr(*, filename: str, content: bytes) -> AttachmentOCRResult:
    if not content:
        return _build_result(status="no_text", warning="No image content was available for OCR.")

    tesseract_path = shutil.which("tesseract")
    if not tesseract_path:
        return _build_result(
            status="skipped",
            warning="OCR engine is not installed on this runtime. Screenshot upload still succeeded.",
        )

    suffix = Path(filename or "upload.jpg").suffix or ".img"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(content)
        temp_path = Path(tmp_file.name)

    try:
        completed = subprocess.run(
            [tesseract_path, str(temp_path), "stdout", "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=OCR_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _build_result(
            status="failed",
            warning="OCR timed out for this screenshot. Upload still succeeded.",
        )
    except Exception:
        return _build_result(
            status="failed",
            warning="OCR could not be completed for this screenshot. Upload still succeeded.",
        )
    finally:
        temp_path.unlink(missing_ok=True)

    extracted_text = completed.stdout or ""
    if completed.returncode != 0 and not extracted_text.strip():
        return _build_result(
            status="failed",
            warning="OCR failed for this screenshot. Upload still succeeded.",
        )

    if not extracted_text.strip():
        return _build_result(
            status="no_text",
            warning="No readable text was detected in this screenshot.",
        )

    return _build_result(status="success", text=extracted_text)
