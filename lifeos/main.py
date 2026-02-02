from fastapi import FastAPI

app = FastAPI(
    title="LifeOS Co-Pilot API",
    version="2.0.1",
    servers=[
        {
            "url": "https://life-os-private-practical-co-pilot.onrender.com",
            "description": "Production (Render)"
        }
    ],
)

# ✅ ADD THIS IMPORT
from lifeos.routes.openapi_alias import router as openapi_alias_router

# ✅ ADD THIS REGISTRATION (NO PREFIX)
app.include_router(openapi_alias_router)

# existing route includes remain unchanged
