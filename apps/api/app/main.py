from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.catalog import router as catalog_router
from app.api.routes.health import router as health_router
from app.api.routes.internal_ingestion import router as internal_ingestion_router
from app.api.routes.stories import router as stories_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="F1 Intelligence API",
    version="0.4.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(stories_router)
app.include_router(catalog_router)
app.include_router(internal_ingestion_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "f1intelligence-api", "status": "ok"}
