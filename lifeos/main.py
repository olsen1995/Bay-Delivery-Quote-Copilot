from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

app = FastAPI(
    title="LifeOS",
    description="Private Practical Co-Pilot",
    version="0.1.0",
)

# 🌐 Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# 🔬 RUNTIME CANON READ — DISABLED (SAFE MODE)
#
# Canon runtime reads are temporarily disabled until a proper
# loader exists. This prevents import and startup failures.
#
# No Canon mutation.
# No governance change.
# No enforcement.
# -------------------------------------------------------------------

CANON_SYSTEM_IDENTITY = None


# -------------------------------------------------------------------
# 🔎 GOVERNANCE STATUS VISIBILITY
#
# Read-only surface.
# Optional data only.
# No coupling to Canon loaders.
# -------------------------------------------------------------------

FREEZE_FILE = Path("lifeos/FREEZE.json")


@app.get("/")
def root():
    return {
        "status": "ok",
        "canon_identity_loaded": False,
        "canon_identity": None,
    }


@app.get("/meta")
def meta():
    """
    Read-only governance and system status surface.
    """
    return {
        "operational_mode": "Day-2 (Operational)",
        "canon_version": None,
        "canon_digest_loaded": False,
        "freeze_active": FREEZE_FILE.exists(),
    }