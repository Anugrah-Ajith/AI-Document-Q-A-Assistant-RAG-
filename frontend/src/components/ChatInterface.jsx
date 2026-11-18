import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Sparkles, BookOpen, AlertCircle, Loader2 } from "lucide-react";
import { CitationCard } from "./CitationCard";

export function ChatInterface({
  messages,
  isLoading,
  onSendMessage,
  quotaRemaining,
  totalDocs,
  selectedDocId,
}) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Helper to highlight citations like [Source: filename, Page: X]
  const renderFormattedText = (text) => {
    if (!text) return null;
    const parts = text.split(/(\[Source:[^\]]+\])/g);
    return parts.map((part, i) => {
      if (part.startsWith("[Source:") && part.endsWith("]")) {
        return (
          <span
            key={i}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "3px",
              padding: "1px 6px",
              margin: "0 2px",
              borderRadius: "4px",
              fontSize: "11px",
              fontWeight: 600,
              backgroundColor: "rgba(99, 102, 241, 0.2)",
              color: "#a5b4fc",
              border: "1px solid rgba(99, 102, 241, 0.4)",
            }}
          >
            <BookOpen size={10} />
            {part.replace("[Source:", "").replace("]", "").trim()}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%" }}>
      {/* Messages Scroll Area */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-icon">
              <Sparkles size={28} />
            </div>
            <h2 className="empty-title">Ask your documents anything</h2>
            <p className="empty-desc">
              {totalDocs > 0
                ? `You have ${totalDocs} document(s) indexed. Ask questions and get answers grounded in your PDFs with verifiable page citations.`
                : "Start by uploading one or more PDF files from the sidebar. Your documents will be chunked, embedded, and stored in ChromaDB for instant Q&A."}
            </p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.role === "user";
            return (
              <div key={msg.id || index} className={`message-row ${isUser ? "user" : "assistant"}`}>
                <div className={`message-avatar ${isUser ? "user" : "assistant"}`}>
                  {isUser ? <User size={16} /> : <Bot size={16} />}
                </div>

                <div className="message-bubble">
                  <div>{renderFormattedText(msg.content)}</div>

                  {/* Render citations if available */}
                  {!isUser && msg.citations && msg.citations.length > 0 && (
                    <div className="citations-wrapper">
                      <div className="citations-header">
                        <BookOpen size={12} />
                        <span>Sources & Citations ({msg.citations.length})</span>
                      </div>
                      <div className="citation-grid">
                        {msg.citations.map((cite, cIdx) => (
                          <CitationCard key={cite.chunk_id || cIdx} citation={cite} index={cIdx} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {isLoading && (
          <div className="message-row assistant">
            <div className="message-avatar assistant">
              <Bot size={16} />
            </div>
            <div className="message-bubble" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} />
              <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                Retrieving relevant chunks & formulating cited answer...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="chat-input-bar">
        <form onSubmit={handleSubmit} className="input-container">
          <input
            type="text"
            className="chat-input"
            placeholder={
              totalDocs === 0
                ? "Upload a PDF first to begin querying..."
                : "Ask a question about your indexed documents..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="btn-send"
            disabled={isLoading || !input.trim() || totalDocs === 0}
          >
            <Send size={14} />
            <span>Ask</span>
          </button>
        </form>
      </div>
    </div>
  );
}
