import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.schemas.chat import ChatMessage, Citation, SessionSummary


class SessionManager:
    """Manages conversational session states, history buffers, and message tracking."""

    def __init__(self):
        # Maps session_id to list of ChatMessage instances
        self._sessions: Dict[str, List[ChatMessage]] = {}
        # Maps session_id to metadata (created_at, last_active)
        self._metadata: Dict[str, Dict[str, str]] = {}

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """Returns the existing session ID or registers a new unique session."""
        now = datetime.now(timezone.utc).isoformat()
        if not session_id or session_id not in self._sessions:
            session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
            self._sessions[session_id] = []
            self._metadata[session_id] = {
                "created_at": now,
                "last_active": now
            }
        else:
            self._metadata[session_id]["last_active"] = now
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[List[Citation]] = None
    ) -> ChatMessage:
        """Appends a new turn to the conversational session history."""
        self.get_or_create_session(session_id)
        msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        msg = ChatMessage(
            id=msg_id,
            role=role,  # type: ignore
            content=content,
            citations=citations,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        self._sessions[session_id].append(msg)
        self._metadata[session_id]["last_active"] = msg.timestamp
        return msg

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Retrieves conversational messages for the given session ID."""
        history = self._sessions.get(session_id, [])
        if limit is not None and limit > 0:
            return history[-limit:]
        return list(history)

    def list_sessions(self) -> List[SessionSummary]:
        """Returns overview information for all recorded active sessions."""
        summaries: List[SessionSummary] = []
        for sess_id, msgs in self._sessions.items():
            meta = self._metadata.get(sess_id, {})
            summaries.append(
                SessionSummary(
                    session_id=sess_id,
                    created_at=meta.get("created_at", ""),
                    last_active=meta.get("last_active", ""),
                    message_count=len(msgs)
                )
            )
        # Sort newest first
        summaries.sort(key=lambda x: x.last_active, reverse=True)
        return summaries

    def clear_session(self, session_id: str) -> bool:
        """Clears messages within a session while keeping the session record."""
        if session_id in self._sessions:
            self._sessions[session_id] = []
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session completely."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._metadata.pop(session_id, None)
            return True
        return False


session_manager = SessionManager()
