
import re
import dateparser
from storage.local_state import (
    get_user_data,
    update_user_data,
    delete_item,
    clear_category,
    clear_all
)

def handle_memory_mode(input_text: str, user_id: str = "user_123"):
    input_text = input_text.lower()
    response = {"summary": "", "steps": [], "priority": "normal", "actions": []}

    # Add Note
    if "remember" in input_text or "note" in input_text:
        note_content = input_text.replace("remember", "").replace("note", "").strip()
        update_user_data(user_id, {"notes": [note_content]})
        response["summary"] = "Note saved 🧠"
        response["steps"].append(f"I've saved: '{note_content}'")
        response["priority"] = "high"
        response["actions"].append({"type": "note", "payload": {"content": note_content}})

    # Add Reminder with optional parsed time
    elif "remind" in input_text or "reminder" in input_text:
        reminder = input_text.replace("remind me", "").replace("reminder", "").strip()
        parsed_time = dateparser.parse(reminder)
        if parsed_time:
            reminder += f" (Parsed time: {parsed_time})"
        update_user_data(user_id, {"reminders": [reminder]})
        response["summary"] = "Reminder added ⏰"
        response["steps"].append(f"I'll remind you about: '{reminder}'")
        response["priority"] = "high"
        response["actions"].append({"type": "reminder", "payload": {"content": reminder}})

    # Delete or Forget
    elif "delete" in input_text or "forget" in input_text or "clear" in input_text:
        if "everything" in input_text:
            clear_all(user_id)
            response["summary"] = "🧹 Everything has been forgotten"
            response["steps"].append("Notes, reminders, and tasks all cleared.")
        elif "reminders" in input_text:
            clear_category(user_id, "reminders")
            response["summary"] = "🧹 Reminders cleared"
            response["steps"].append("All reminders have been wiped.")
        elif "notes" in input_text:
            clear_category(user_id, "notes")
            response["summary"] = "🧹 Notes cleared"
            response["steps"].append("All notes have been wiped.")
        elif "tasks" in input_text:
            clear_category(user_id, "tasks")
            response["summary"] = "🧹 Tasks cleared"
            response["steps"].append("All tasks have been wiped.")
        else:
            keyword = input_text.replace("delete", "").replace("forget", "").replace("clear", "").strip()
            deleted = False
            for cat in ["notes", "reminders", "tasks"]:
                if delete_item(user_id, cat, keyword):
                    response["summary"] = f"❌ Removed items matching '{keyword}'"
                    response["steps"].append(f"From category: {cat}")
                    deleted = True
                    break
            if not deleted:
                response["summary"] = "Nothing matched your deletion request"
                response["steps"].append("Try saying 'delete note about groceries'")

    # Memory Search
    elif "what" in input_text or "do i have" in input_text or "show" in input_text:
        data = get_user_data(user_id)
        keyword = None
        match = re.search(r"\b(?:about|for|on)\s+(.*)", input_text)
        if match:
            keyword = match.group(1).strip()

        if keyword:
            found = []
            for category, items in data.items():
                for item in items:
                    if keyword.lower() in item.lower():
                        found.append(f"{category}: {item}")
            if found:
                response["summary"] = f"🔍 Found {len(found)} match(es) for '{keyword}'"
                response["steps"].extend(found)
            else:
                response["summary"] = f"🔎 No results for '{keyword}'"
                response["steps"].append("Try phrasing it differently or check spelling.")
        else:
            response["summary"] = "🧠 Memory Snapshot"
            response["steps"].extend([
                f"📝 Notes: {', '.join(data.get('notes', []) or ['None'])}",
                f"⏰ Reminders: {', '.join(data.get('reminders', []) or ['None'])}",
                f"✅ Tasks: {', '.join(data.get('tasks', []) or ['None'])}"
            ])

    # Fallback
    else:
        response["summary"] = "Hmm, I didn't catch that fully 🤔"
        response["steps"].append("Try saying things like:")
        response["steps"].append("- 'Remember this: buy snacks'")
        response["steps"].append("- 'Show my reminders'")
        response["steps"].append("- 'Forget everything'")

    return response
