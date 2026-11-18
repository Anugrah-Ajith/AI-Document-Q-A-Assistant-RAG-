import React from "react";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { api } from "../services/api";

export function SessionList({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onSessionsUpdated,
  onError,
}) {
  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    try {
      await api.deleteSession(sessionId);
      if (sessionId === currentSessionId) {
        onNewSession();
      }
      await onSessionsUpdated();
    } catch (err) {
      onError("Failed to delete session history.");
    }
  };

  return (
    <div>
      <div className="section-title">
        <span>Chat Sessions</span>
        <span>{sessions.length}</span>
      </div>

      <button className="btn-new-chat" onClick={onNewSession} style={{ marginBottom: "10px" }}>
        <Plus size={14} />
        <span>New Chat Session</span>
      </button>

      <div className="session-list">
        {sessions.map((sess) => {
          const isActive = sess.session_id === currentSessionId;
          const displayId = sess.session_id.replace("sess_", "").slice(0, 8);

          return (
            <div
              key={sess.session_id}
              className={`session-item ${isActive ? "active" : ""}`}
              onClick={() => onSelectSession(sess.session_id)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
                <MessageSquare size={13} style={{ flexShrink: 0 }} />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  Session {displayId}
                </span>
                <span style={{ fontSize: "10px", color: "var(--text-dim)" }}>
                  ({sess.message_count})
                </span>
              </div>
              <button
                className="btn-icon"
                title="Delete Session"
                onClick={(e) => handleDeleteSession(sess.session_id, e)}
              >
                <Trash2 size={12} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
