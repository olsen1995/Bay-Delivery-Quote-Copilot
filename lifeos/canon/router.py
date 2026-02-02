from fastapi import APIRouter

from canon.snapshot import get_snapshot
from canon.digest import get_digest
from canon.schemas import get_schemas
from canon.trees import get_trees


class CanonRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/canon")

        self.router.add_api_route(
            "/snapshot",
            get_snapshot,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/digest",
            get_digest,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/schemas",
            get_schemas,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/trees",
            get_trees,
            methods=["GET"],
        )
