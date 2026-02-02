from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware

# ─────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="LifeOS Co-Pilot API",
    version="2.0.1",
    servers=[
        {
            "url": "https://life-os-private-practical-co-pilot.onrender.com",
            "description": "Production (Render)",
        }
    ],
)

# ─────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# Routers (runtime-relative imports only)
# ─────────────────────────────────────────────────────────────

from routes.mode_router import ModeRouter
from routes.memory_read_router import router as memory_read_router
from routes.healthz import healthz_router
from routes.openapi_alias import router as openapi_alias_router

router = ModeRouter()

app.include_router(router.router)
app.include_router(memory_read_router)
app.include_router(healthz_router)

# 🔧 OpenAPI alias router (root-level, no prefix)
app.include_router(openapi_alias_router)

# ─────────────────────────────────────────────────────────────
# Simple /ask Endpoint (unchanged)
# ─────────────────────────────────────────────────────────────

@app.post("/ask")
def ask(message: str = Form(...), user_id: str = Form(...)):
    return {
        "summary": f"You said: {message}",
        "user_id": user_id,
    }
