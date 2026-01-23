from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from mode_router import ModeRouter
from modes.dayplanner import handle_dayplanner_mode
from modes.lifecoach import handle_lifecoach_mode
from modes.fixit import handle_fixit_mode

# Initialize FastAPI app
app = FastAPI()

# Serve .well-known for plugin manifest
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Initialize the ModeRouter
router = ModeRouter()

# Input model
class UserInput(BaseModel):
    input: str

# Route user input to the correct mode handler
@app.post("/route")
async def route_input(data: UserInput):
    mode = router.detect_mode(data.input)

    if mode == "DayPlanner":
        return {
            "mode": mode,
            "result": handle_dayplanner_mode(data.input)
        }

    elif mode == "LifeCoach":
        return {
            "mode": mode,
            "result": handle_lifecoach_mode(data.input)
        }

    elif mode == "FixIt":
        return {
            "mode": mode,
            "result": handle_fixit_mode(data.input)
        }

    return {"mode": mode, "result": "No logic implemented yet."}


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
