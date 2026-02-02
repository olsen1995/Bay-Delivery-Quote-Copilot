from fastapi import FastAPI

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

# 🔧 PHASE G FIX — register OpenAPI alias router
from lifeos.routes.openapi_alias import router as openapi_alias_router

app.include_router(openapi_alias_router)

# 🔒 all other existing includes remain unchanged
