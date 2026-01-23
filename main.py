from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import List, Dict, Any

from mode_router import ModeRouter
from modes.device_optimizer import optimize_device, DeviceState, OptimizationSuggestion
from modes.kitchen import handle_kitchen_mode, KitchenInput, KitchenResponse
from storage.json_store import save_user_data, load_user_data

# Initialize FastAPI app
app = FastAPI()

# Serve .well-known for plugin manifest
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

router = ModeRouter()

# ---------- Models ----------

class UserInput(BaseModel):
    input: str

class SaveRequest(BaseModel):
    user_id: str
    key: str
    value: Dict[str, Any]

class LoadRequest(BaseModel):
    user_id: str
    key: str

# ---------- Routes ----------

@app.post("/route")
async def route_input(data: UserInput):
    mode = router.detect_mode(data.input)
    result = router.handle_mode(mode, data.input)
    return {"mode": mode, "result": result}

@app.post("/device-optimizer", response_model=List[OptimizationSuggestion])
async def run_device_optimizer(state: DeviceState):
    return optimize_device(state)

@app.post("/kitchen", response_model=KitchenResponse)
async def run_kitchen_mode(data: KitchenInput):
    return handle_kitchen_mode(data)

# ---------- Persistence ----------

@app.post("/save")
async def save_data(req: SaveRequest):
    user_data = load_user_data(req.user_id)
    user_data[req.key] = req.value
    save_user_data(req.user_id, user_data)
    return {"status": "saved", "key": req.key}

@app.post("/load")
async def load_data(req: LoadRequest):
    user_data = load_user_data(req.user_id)
    return {
        "key": req.key,
        "value": user_data.get(req.key)
    }

# ---------- OpenAPI ----------

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="LifeOS Co-Pilot",
        version="1.0.0",
        description="Routes your input to real-life task modes.",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://zeke-unattaining-wendy.ngrok-free.dev"}
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
