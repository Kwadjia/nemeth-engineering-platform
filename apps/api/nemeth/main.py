"""FastAPI application factory."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nemeth import __version__
from nemeth.core.config import Settings, get_settings
from nemeth.core.errors import install_error_handlers
from nemeth.core.logging import RequestContextMiddleware, configure_logging
from nemeth.modules.bom.router import router as bom_router
from nemeth.modules.components.router import router as components_router
from nemeth.modules.experiments.router import router as experiments_router
from nemeth.modules.products.router import router as products_router
from nemeth.modules.prototypes.router import router as prototypes_router
from nemeth.modules.system.router import router as system_router
from nemeth.modules.testing.router import router as testing_router
from nemeth.modules.watches.router import router as watches_router

DESCRIPTION = """
Internal engineering platform for **NEMETH — Detroit**: product definition, components
with immutable revisions, recursive bills of materials, and (in later slices) prototypes,
experiments, measurements and serialized watch genealogy.

Errors are returned as RFC 9457 problem details (`application/problem+json`).
Resources are addressed by UUID or by human identifier (`N1-MVT-002`).
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=DESCRIPTION,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        debug=settings.debug,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)

    api = APIRouter(prefix=settings.api_prefix)
    api.include_router(system_router)
    api.include_router(products_router)
    api.include_router(components_router)
    api.include_router(bom_router)
    api.include_router(prototypes_router)
    api.include_router(experiments_router)
    api.include_router(testing_router)
    api.include_router(watches_router)
    app.include_router(api)
    return app


app = create_app()
