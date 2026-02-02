from fastapi import APIRouter
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from main import app

router = APIRouter()


@router.get("/.well-known/openapi.json", include_in_schema=False)
def openapi_alias():
    return JSONResponse(
        get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
    )
