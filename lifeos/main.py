from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.metrics import get_metrics
from canon.router import CanonRouter

app = FastAPI()

# CORS (per prior config — unchanged)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check (required for Render)
@app.get("/health")
def health():
    return {"status": "ok"}

# Canon router (read-only)
canon_router = CanonRouter()
app.include_router(canon_router.router)
