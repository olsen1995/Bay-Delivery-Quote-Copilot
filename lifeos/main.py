from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from lifeos.routes.mode_router import ModeRouter
from lifeos.storage.memory_manager import MemoryManager

app = FastAPI()

# 🧠 Mount router instance
router = ModeRouter()

# 🌐 Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ /ask: Simple AI response route
@app.post("/ask")
def ask(message: str = Form(...), user_id: str = Form(...)):
    # Example response logic (you can improve this)
    return {"summary": f"You said: {message}", "user_id": user_id}

# ✅ /memory GET: Retrieve memory
@app.get("/memory")
def get_memory(user_id: str):
    mm = MemoryManager(user_id)
    return mm.get_all()

# ✅ /memory POST: Clear memory
@app.post("/memory")
def clear_memory(confirm: str = Form(...), user_id: str = Form(...)):
    if confirm.lower() == "yes":
        mm = MemoryManager(user_id)
        mm.delete_all()
        return RedirectResponse(url="/memory?user_id=" + user_id, status_code=303)
    raise HTTPException(status_code=400, detail="Confirmation required to clear memory")

# ✅ /route: Auto-route to best mode
@app.post("/route")
def handle_route(input: str = Form(...)):
    state = {}
    mode = router.route(input, state)
    return mode.run(input, state)
