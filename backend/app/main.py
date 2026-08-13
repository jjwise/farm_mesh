"""FastAPI app entrypoint."""

from fastapi import FastAPI
from sqlalchemy import text

from app.api.ingest import router as ingest_router
from app.api.lines import router as lines_router
from app.config import settings
from app.database import Base, engine


def create_app() -> FastAPI:
    """Build the FastAPI application and initialize schema."""

    Base.metadata.create_all(bind=engine)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(ingest_router)
    app.include_router(lines_router)

    @app.get("/healthz", tags=["system"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["system"])
    def readiness_check() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app


app = create_app()
