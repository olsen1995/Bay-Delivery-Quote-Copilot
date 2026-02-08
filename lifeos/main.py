from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 🧠 Canon read-gate (existing utility)
from lifeos.canon.read_gate import read_canon_file

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
# 🔬 RUNTIME CANON READ PILOT (M17.2)
#
# Intentional constraints:
# - ONE Canon artifact
# - READ-ONLY
# - Optional (safe fallback)
# - No abstraction
# - No enforcement
#
# ⚠️ Pilot only — do not generalize
# -------------------------------------------------------------------

CANON_SYSTEM_IDENTITY = None

try:
    CANON_SYSTEM_IDENTITY = read_canon_file(
        "metadata/system_identity.json"
    )
except Exception:
    # Canon is optional at runtime for this pilot.
    # Failure MUST NOT block startup.
    CANON_SYSTEM_IDENTITY = None


@app.get("/")
def root():
    """
    Minimal runtime surface.

    If Canon metadata is available, expose it passively.
    Otherwise, operate normally.
    """
    return {
        "status": "ok",
        "canon_identity_loaded": CANON_SYSTEM_IDENTITY is not None,
        "canon_identity": CANON_SYSTEM_IDENTITY,
    }