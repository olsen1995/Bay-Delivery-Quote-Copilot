
import os
import json
from datetime import datetime
from typing import Optional

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def log_action(user_id: str, action_type: str, input_text: str, metadata: Optional[dict] = None):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "action": action_type,
        "input": input_text,
        "metadata": metadata or {}
    }
    file_path = os.path.join(LOG_DIR, f"{user_id}.jsonl")
    with open(file_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
