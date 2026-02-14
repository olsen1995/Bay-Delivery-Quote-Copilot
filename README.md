
# 🧠 Bay Delivery Quote Copilot Co-Pilot

Your private, voice-friendly, ADHD-aware ChatGPT plugin for managing real-life stuff like reminders, notes, tasks, and more.

---

## ✨ Features

- ✅ Add and retrieve notes, reminders, and tasks

- 🕰️ Understands natural time: “in 30 minutes”, “next Friday”

- 🔍 Search memory: “What do I have about groceries?”

- ❌ Delete items or entire categories: “Forget all notes”

- 🧠 Per-user persistent memory (JSON-based)

- 🔁 Smart intent routing via `/ask` endpoint

- 🎙️ Voice-friendly command parsing + fallback suggestions

- 📜 Per-user usage logging (`/logs/user_id.jsonl`)

- 🧩 Full ChatGPT Plugin integration via `ai-plugin.json`

---

## 🛠️ Setup

### 📦 Requirements

- Python 3.9+

- `uvicorn`, `fastapi`, `python-dotenv`, `openai`, `dateparser`

### 🚀 Running locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 10000

```json

---

## 📡 API Endpoint

```json
POST /ask
{
  "message": "Remind me to take my vitamins at 8am",
  "user_id": "user_123",
  "adhd_mode": true
}

```json

Returns structured JSON with summary, steps, actions, and priority.

---

## 🤖 ChatGPT Plugin Integration

Hosted at:

- Plugin manifest: `/.well-known/ai-plugin.json`

- OpenAPI spec: `/openapi.json`

- Logo: `/logo.png`

Follow ChatGPT > Settings > Actions > Develop Plugin

---

## 📁 Folder Structure

```json
├── main.py                  # Entrypoint with /ask endpoint
├── mode_router.py           # Keyword routing to modes
├── modes/                   # Mode handlers (memory, fixit, etc)
├── storage/
│   ├── local_state.py       # File-based user memory store
│   └── user_data/           # Per-user memory files
├── logs/                    # Per-user usage logs
├── response_formatter.py    # Unified JSON formatter
├── ai-plugin.json           # Plugin manifest
├── openapi.json             # OpenAPI schema

```json

---

## 📬 Contact & Support

- `support@yourdomain.com` (update in `ai-plugin.json`)

- Powered by FastAPI + OpenAI + Render

---

## 📄 License

MIT
