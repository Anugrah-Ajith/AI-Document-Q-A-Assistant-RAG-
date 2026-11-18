from datetime import datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Source reference for retrieved knowledge chunks."""
    filename: str = Field(description="Name of the PDF file containing the source text")
    page: int = Field(ge=1, description="Page number where the chunk appears")
    chunk_id: str = Field(description="Unique identifier of the referenced chunk")
    snippet: str = Field(description="Excerpt preview of the source text")
    relevance_score: float = Field(description="Cosine similarity score (0.0 to 1.0)")


class ChatMessage(BaseModel):
    """Single message within a conversational session."""
    id: str = Field(description="Unique message identifier")
    role: Literal["user", "assistant", "system"] = Field(description="Author role")
    content: str = Field(description="Message text")
    citations: Optional[List[Citation]] = Field(default=None, description="Source citations for assistant responses")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp"
    )


class ChatRequest(BaseModel):
    """Incoming user chat query."""
    message: str = Field(..., min_length=1, max_length=4000, description="User's query")
    session_id: Optional[str] = Field(default=None, description="Optional conversational session ID")
    top_k: Optional[int] = Field(default=None, ge=1, le=15, description="Number of context chunks to retrieve")
    filter_document_id: Optional[str] = Field(default=None, description="Optional document ID to restrict search")


class ChatResponse(BaseModel):
    """AI answer accompanied by citations and session metadata."""
    session_id: str
    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    chunks_retrieved: int = 0
    rate_limit_remaining: int = 20
    status: str = "success"


class SessionSummary(BaseModel):
    """Metadata summary for a chat session."""
    session_id: str
    created_at: str
    last_active: str
    message_count: int


class SessionListResponse(BaseModel):
    """List of all active user sessions."""
    sessions: List[SessionSummary]
    total_sessions: int


class SessionHistoryResponse(BaseModel):
    """Full message history for an active session."""
    session_id: str
    messages: List[ChatMessage]
    total_messages: int
