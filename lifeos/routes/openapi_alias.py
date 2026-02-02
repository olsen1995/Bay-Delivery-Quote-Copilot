from fastapi import APIRouter, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/.well-known/openapi.json", include_in_schema=False)
def openapi_alias(request: Request):
    app = request.app
    return JSONResponse(
        get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
    )
