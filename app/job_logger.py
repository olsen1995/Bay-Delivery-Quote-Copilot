import json
from datetime import datetime
from pathlib import Path

JOB_LOG_FILE = Path("jobs.json")


def _load_jobs():
    if JOB_LOG_FILE.exists():
        with open(JOB_LOG_FILE, "r") as f:
            return json.load(f)
    return []


def _save_jobs(jobs):
    with open(JOB_LOG_FILE, "w") as f:
        json.dump(jobs, f, indent=4)


def log_job(data: dict) -> dict:
    jobs = _load_jobs()

    entry = {
        "id": len(jobs),
        "timestamp": datetime.now().isoformat(),
        "status": "quoted",  # default status
        "data": data
    }

    jobs.append(entry)
    _save_jobs(jobs)

    return entry


def get_jobs():
    return _load_jobs()


def update_job_status(job_id: int, status: str):
    jobs = _load_jobs()

    if job_id < 0 or job_id >= len(jobs):
        return {"error": "Job not found"}

    jobs[job_id]["status"] = status
    _save_jobs(jobs)

    return jobs[job_id]
