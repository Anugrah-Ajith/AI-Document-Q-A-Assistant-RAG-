import React, { useState, useRef } from "react";
import { UploadCloud, FileText, Trash2, Loader2, CheckCircle2 } from "lucide-react";
import { api } from "../services/api";

export function DocumentUpload({ documents, onDocumentsUpdated, onError, onNotice }) {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleUpload = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      onError("Only PDF documents (.pdf) can be uploaded.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      onError("File exceeds the 25MB maximum limit.");
      return;
    }

    try {
      setIsUploading(true);
      const res = await api.uploadDocument(file);
      onNotice(`Indexed '${res.filename}' (${res.total_pages} pages, ${res.total_chunks} chunks).`);
      await onDocumentsUpdated();
    } catch (err) {
      onError(err.message || "Failed to upload and index PDF.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (docId, filename, e) => {
    e.stopPropagation();
    if (!window.confirm(`Remove '${filename}' and its vector embeddings?`)) return;

    try {
      await api.deleteDocument(docId);
      onNotice(`Removed '${filename}' from vector store.`);
      await onDocumentsUpdated();
    } catch (err) {
      onError(err.message || "Failed to delete document.");
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div>
      <div className="section-title">
        <span>Knowledge Base</span>
        <span>{documents.length} Files</span>
      </div>

      {/* Dropzone */}
      <div
        className={`dropzone ${dragActive ? "active" : ""}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        />
        <div className="dropzone-icon">
          {isUploading ? (
            <Loader2 size={24} className="spin" style={{ animation: "spin 1s linear infinite" }} />
          ) : (
            <UploadCloud size={24} />
          )}
        </div>
        <div className="dropzone-label">
          {isUploading ? "Extracting & Embedding..." : "Drop PDF or browse"}
        </div>
        <div className="dropzone-hint">Preserves pages & creates overlapping chunks</div>
      </div>

      {/* Document List */}
      <div className="doc-list" style={{ marginTop: "12px" }}>
        {documents.map((doc) => (
          <div key={doc.document_id} className="doc-card">
            <FileText size={16} color="#818cf8" style={{ flexShrink: 0 }} />
            <div className="doc-info">
              <div className="doc-filename" title={doc.filename}>
                {doc.filename}
              </div>
              <div className="doc-meta">
                <span>{doc.total_pages} {doc.total_pages === 1 ? "page" : "pages"}</span>
                <span>•</span>
                <span>{doc.total_chunks} chunks</span>
              </div>
            </div>
            <button
              className="btn-icon"
              title="Delete Document"
              onClick={(e) => handleDelete(doc.document_id, doc.filename, e)}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
