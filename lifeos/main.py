from fastapi import FastAPI, Request, Form, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from lifeos.routes.mode_router import ModeRouter

from lifeos.auth import verify_api_key

app = FastAPI()
mode_router = ModeRouter()

# Mount static folder for well-known
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="well-known")


@app.post("/ask")
async def ask(
    request: Request,
    message: str = Form(...),
    user_id: str = Form(...),
    x_api_key: str = Header(None)
):
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")

    state = {"user_id": user_id}
    mode = mode_router.route(message, state)
    response = mode.handle(message, state)
    return {"summary": response}


@app.get("/memory")
async def get_memory(user_id: str):
    from lifeos.storage.memory_manager import MemoryManager
    mm = MemoryManager(user_id)
    memory = mm.get_memory()
    return {"memory": memory}


@app.post("/memory")
async def clear_memory(user_id: str = Form(...), confirm: str = Form(...)):
    if confirm.lower() == "yes":
        from lifeos.storage.memory_manager import MemoryManager
        mm = MemoryManager(user_id)
        mm.clear_memory()
    return RedirectResponse(url="/", status_code=303)
