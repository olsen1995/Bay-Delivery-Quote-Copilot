import json
from datetime import datetime
from pathlib import Path

JOB_LOG_FILE = Path("jobs.json")


def log_job(data: dict) -> dict:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }

    if JOB_LOG_FILE.exists():
        with open(JOB_LOG_FILE, "r") as f:
            jobs = json.load(f)
    else:
        jobs = []

    jobs.append(entry)

    with open(JOB_LOG_FILE, "w") as f:
        json.dump(jobs, f, indent=4)

    return entry
