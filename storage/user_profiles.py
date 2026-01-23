from pathlib import Path
import json
from typing import Dict, Any

PROFILE_DIR = Path("profiles")
PROFILE_DIR.mkdir(exist_ok=True)

def get_profile_path(user_id: str) -> Path:
    return PROFILE_DIR / f"{user_id}.json"

def load_profile(user_id: str) -> Dict[str, Any]:
    path = get_profile_path(user_id)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_profile(user_id: str, data: Dict[str, Any]) -> None:
    path = get_profile_path(user_id)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
