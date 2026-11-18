from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.rate_limiter import rate_limiter
from app.core.session_manager import session_manager
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SessionHistoryResponse,
    SessionListResponse,
)
from app.services.rag_service import RAGService

router = APIRouter(prefix="/api/v1/chat", tags=["Chat & RAG"])

_rag_service = RAGService()


def get_rag_service() -> RAGService:
    return _rag_service


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question against indexed documents",
    description="Retrieves the most relevant document chunks and generates an AI answer with page-level citations."
)
async def chat_endpoint(
    req: ChatRequest,
    request: Request,
    rag_service: RAGService = Depends(get_rag_service),
) -> ChatResponse:
    # 1. Enforce per-client / per-IP rate limit
    client_key = (
        request.headers.get("x-user-id")
        or (req.session_id if req.session_id else None)
        or (request.client.host if request.client else "anonymous-client")
    )
    remaining_quota = rate_limiter.enforce(request, identifier=client_key)

    # 2. Acquire or initialize session ID
    session_id = session_manager.get_or_create_session(req.session_id)

    # 3. Clean user message
    cleaned_query = req.message.strip()
    if not cleaned_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    # 4. Execute RAG retrieval and generation
    answer, citations, chunks_count = await rag_service.answer_question(
        question=cleaned_query,
        session_id=session_id,
        top_k=req.top_k,
        filter_document_id=req.filter_document_id
    )

    return ChatResponse(
        session_id=session_id,
        question=cleaned_query,
        answer=answer,
        citations=citations,
        chunks_retrieved=chunks_count,
        rate_limit_remaining=remaining_quota,
        status="success"
    )


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List all conversational sessions",
    description="Returns metadata, message count, and last active timestamp for each session."
)
async def list_sessions() -> SessionListResponse:
    sessions = session_manager.list_sessions()
    return SessionListResponse(
        sessions=sessions,
        total_sessions=len(sessions)
    )


@router.get(
    "/sessions/{session_id}/history",
    response_model=SessionHistoryResponse,
    summary="Get chat history for a session",
    description="Retrieves the complete sequence of messages and attached citations for the session."
)
async def get_session_history(session_id: str) -> SessionHistoryResponse:
    messages = session_manager.get_history(session_id)
    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages,
        total_messages=len(messages)
    )


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a chat session",
    description="Removes the session and its history from memory."
)
async def delete_session(session_id: str):
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )
    return {"message": f"Session '{session_id}' successfully deleted.", "status": "success"}
