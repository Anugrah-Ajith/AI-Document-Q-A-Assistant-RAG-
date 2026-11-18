import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys
from pathlib import Path

# Ensure backend root is on sys.path so 'app' and internal imports resolve properly
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import get_settings
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("document_qa")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    logger.info("Starting RAG Document Q&A Assistant backend service...")
    logger.info(f"LLM Model: {settings.LLM_MODEL} | Embedding: {settings.EMBEDDING_MODEL}")
    logger.info(f"Vector Store Directory: {settings.CHROMA_PERSIST_DIR}")
    yield
    logger.info("Shutting down RAG Document Q&A Assistant backend service.")


app = FastAPI(
    title="RAG Document Q&A API",
    description="High-performance Retrieval-Augmented Generation API with page-level citations, session history, and rate limiting.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

from fastapi.staticfiles import StaticFiles

# Setup CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred.", "error": str(exc)}
    )

# Register routers
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(chat_router)

# Mount React static files after API routes so API endpoints take priority
frontend_dist = backend_dir.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "message": "RAG Document Q&A Assistant Backend is operational.",
            "documentation": "/docs",
            "health": "/api/v1/health"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
