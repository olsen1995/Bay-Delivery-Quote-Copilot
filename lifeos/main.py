from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from lifeos.routes.canon_router import CanonRouter
import datetime
import logging
import sys
import json

app = FastAPI()

# 🌐 Temporary permissive CORS for Render deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Lock down CORS for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🕓 Record startup time
START_TIME = datetime.datetime.utcnow()

# 🧠 Mount Canon read-only router under /canon
canon_router = CanonRouter()
app.include_router(canon_router.router, prefix="/canon")

# 🩺 Health check endpoint (non-blocking)
@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime": (datetime.datetime.utcnow() - START_TIME).total_seconds(),
        "version": "1.0.0",
        "timestamp": START_TIME.isoformat() + "Z"
    }

# 📋 Structured JSON logger
logger = logging.getLogger("lifeos")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt='{"event": "%(message)s", "level": "%(levelname)s", "time": "%(asctime)s"}'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# 🚨 Log uncaught exceptions (without modifying response)
@app.middleware("http")
async def log_exceptions(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(json.dumps({
            "event": "uncaught_exception",
            "path": request.url.path,
            "error": str(exc)
        }))
        raise  # Maintain original HTTP behavior

# 🟢 Structured boot confirmation
logger.info("startup_complete")
