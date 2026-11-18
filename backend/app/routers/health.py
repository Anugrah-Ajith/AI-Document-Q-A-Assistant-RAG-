from typing import Any, Dict
from fastapi import APIRouter, Depends
from app.config import Settings, get_settings
from app.services.vector_store import VectorStoreService

router = APIRouter(prefix="/api/v1/health", tags=["Health"])

_vector_store = VectorStoreService()


def get_vector_store() -> VectorStoreService:
    return _vector_store


@router.get("", summary="System health check and vector store statistics")
async def health_check(
    settings: Settings = Depends(get_settings),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> Dict[str, Any]:
    stats = vector_store.get_stats()
    return {
        "status": "healthy",
        "service": "RAG Document Q&A Assistant",
        "llm_model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "vector_store": stats,
        "has_openai_key": bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("your_openai"))
    }
