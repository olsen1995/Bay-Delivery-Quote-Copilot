from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import List

from mode_router import ModeRouter
from modes.dayplanner import handle_dayplanner_mode
from modes.lifecoach import handle_lifecoach_mode
from modes.fixit import handle_fixit_mode
from modes.device_optimizer import optimize_device, DeviceState, OptimizationSuggestion
from modes.kitchen import handle_kitchen_mode, KitchenInput, KitchenResponse

# Initialize FastAPI app
app = FastAPI()

# Serve .well-known for plugin manifest
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Initialize the ModeRouter
router = ModeRouter()

# Input model for /route
class UserInput(BaseModel):
    input: str

# Route user input to the correct mode handler
@app.post("/route")
async def route_input(data: UserInput):
    mode = router.detect_mode(data.input)
    result = router.handle_mode(mode, data.input)
    return {"mode": mode, "result": result}

# POST: Run Device Optimizer
@app.post("/device-optimizer", response_model=List[OptimizationSuggestion])
async def run_device_optimizer(state: DeviceState):
    return optimize_device(state)

# POST: Run Kitchen Planner
@app.post("/kitchen", response_model=KitchenResponse)
async def run_kitchen_mode(data: KitchenInput):
    return handle_kitchen_mode(data)

# Inject OpenAPI "servers" field so GPT plugin accepts the schema
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
        {"url": "https://zeke-unattaining-wendy.ngrok-free.dev"}  # Update this for deployment
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
