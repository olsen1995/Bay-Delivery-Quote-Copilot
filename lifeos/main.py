from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from canon.router import CanonRouter
from meta.version import get_version
from routes.openapi_alias import router as openapi_router

app = FastAPI(
    title="LifeOS API",
    version="1.0.0",
    description="Stable read-only API surface for LifeOS Canon"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/meta/version")
def meta_version():
    return get_version()


canon_router = CanonRouter()
app.include_router(canon_router.router)

# OpenAPI discovery alias for GPT Actions
app.include_router(openapi_router)
