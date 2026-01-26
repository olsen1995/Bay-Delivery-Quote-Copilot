from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Serve the .well-known folder for ai-plugin.json
app.mount(
    "/.well-known",
    StaticFiles(directory=os.path.join(os.getcwd(), "static", "well-known")),
    name="well-known",
)

# Serve openapi.json from root
@app.get("/openapi.json")
async def get_openapi():
    return FileResponse("openapi.json")
