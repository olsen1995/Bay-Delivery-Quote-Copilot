
import os
import json

BASE_PATH = os.path.join(os.path.dirname(__file__), "user_data")

def _get_user_file_path(user_id: str) -> str:
    os.makedirs(BASE_PATH, exist_ok=True)
    return os.path.join(BASE_PATH, f"{user_id}.json")

def get_user_data(user_id: str) -> dict:
    file_path = _get_user_file_path(user_id)
    if not os.path.exists(file_path):
        return {"notes": [], "reminders": [], "tasks": []}
    with open(file_path, "r") as f:
        return json.load(f)

def update_user_data(user_id: str, new_data: dict):
    file_path = _get_user_file_path(user_id)
    data = get_user_data(user_id)
    for key, value in new_data.items():
        if key in data and isinstance(data[key], list):
            data[key].extend(value)
        else:
            data[key] = value
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def clear_user_data(user_id: str):
    file_path = _get_user_file_path(user_id)
    if os.path.exists(file_path):
        os.remove(file_path)

def delete_item(user_id: str, category: str, keyword: str) -> bool:
    data = get_user_data(user_id)
    items = data.get(category, [])
    updated_items = [item for item in items if keyword.lower() not in item.lower()]
    data[category] = updated_items
    with open(_get_user_file_path(user_id), "w") as f:
        json.dump(data, f, indent=2)
    return len(items) != len(updated_items)

def clear_category(user_id: str, category: str):
    data = get_user_data(user_id)
    data[category] = []
    with open(_get_user_file_path(user_id), "w") as f:
        json.dump(data, f, indent=2)

def clear_all(user_id: str):
    with open(_get_user_file_path(user_id), "w") as f:
        json.dump({"notes": [], "reminders": [], "tasks": []}, f, indent=2)
