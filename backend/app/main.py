from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.router import router
from app.core.config import get_settings
from app.db.session import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        engine.dispose()

def create_app() -> FastAPI:
    dev = get_settings().environment == 'development'
    application = FastAPI(title='Crossborder AI Agent API', lifespan=lifespan,
        docs_url='/docs' if dev else None, redoc_url='/redoc' if dev else None,
        openapi_url='/openapi.json' if dev else None)
    application.include_router(router, prefix='/api/v1')
    return application

app = create_app()
