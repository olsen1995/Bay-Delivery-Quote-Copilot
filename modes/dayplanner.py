from typing import List, Dict

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def generate_weekly_schedule(tasks: List[str]) -> Dict[str, List[str]]:
    """
    Distribute tasks across the week, one per day starting from Monday.
    Always returns Dict[str, List[str]].
    """

    # ✅ FIX: error is returned as a list, not a string
    if not tasks:
        return {"Error": ["No tasks provided."]}

    schedule: Dict[str, List[str]] = {day: [] for day in DAYS}

    for i, task in enumerate(tasks):
        day = DAYS[i % len(DAYS)]
        hour = 9 + (i % 8)  # 9am–4pm
        schedule[day].append(f"{hour}:00 - {task}")

    return schedule
