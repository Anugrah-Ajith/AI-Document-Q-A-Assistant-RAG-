/**
 * API client communicating with FastAPI backend endpoints.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, options);

  let data;
  try {
    data = await response.json();
  } catch (err) {
    data = { detail: "Unable to parse server response." };
  }

  if (!response.ok) {
    const error = new Error(data.detail || `HTTP Error ${response.status}`);
    error.status = response.status;
    error.data = data;
    error.retryAfter = response.headers.get("Retry-After");
    throw error;
  }

  return data;
}

export const api = {
  // System Health
  async getHealth() {
    return request("/api/v1/health");
  },

  // Document Management
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append("file", file);
    return request("/api/v1/documents/upload", {
      method: "POST",
      body: formData,
    });
  },

  async listDocuments() {
    return request("/api/v1/documents");
  },

  async deleteDocument(documentId) {
    return request(`/api/v1/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  // Conversational Chat & Citations
  async sendChatMessage({ message, sessionId, topK, filterDocId }) {
    return request("/api/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId || null,
        top_k: topK || 4,
        filter_document_id: filterDocId || null,
      }),
    });
  },

  // Sessions
  async listSessions() {
    return request("/api/v1/chat/sessions");
  },

  async getSessionHistory(sessionId) {
    return request(`/api/v1/chat/sessions/${sessionId}/history`);
  },

  async deleteSession(sessionId) {
    return request(`/api/v1/chat/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },
};
