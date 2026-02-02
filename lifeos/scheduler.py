
from apscheduler.schedulers.background import BackgroundScheduler
from openai import OpenAI
from storage.local_state import get_user_data, update_user_data
import logging

client = OpenAI()

def generate_suggestions(user_id: str = "user_123"):
    memory = get_user_data(user_id)

    prompt = f"""
You are a helpful assistant for an ADHD user.
Based on this memory data, suggest 1–3 small, helpful, non-overwhelming actions:

Memory:
{memory}
"""

    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )
    content = res.choices[0].message.content
    suggestions = content.strip() if content else "No suggestions returned."

    update_user_data(user_id, {"suggestions": [suggestions]})
    logging.info(f"✅ Suggestions saved for {user_id}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(generate_suggestions, "cron", hour=9, minute=0)
    scheduler.start()
