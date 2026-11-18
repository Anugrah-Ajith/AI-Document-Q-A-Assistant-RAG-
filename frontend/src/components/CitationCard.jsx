import React, { useState } from "react";
import { BookOpen, ChevronDown, ChevronUp } from "lucide-react";

export function CitationCard({ citation, index }) {
  const [expanded, setExpanded] = useState(false);

  const scorePercent = citation.relevance_score
    ? Math.round(citation.relevance_score * 100)
    : null;

  return (
    <div
      className={`citation-card ${expanded ? "expanded" : ""}`}
      onClick={() => setExpanded(!expanded)}
      title="Click to toggle snippet excerpt"
    >
      <div className="citation-header-row">
        <span className="citation-source-tag">
          <BookOpen size={12} />
          {citation.filename} • Page {citation.page}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {scorePercent !== null && (
            <span className="citation-score">{scorePercent}% match</span>
          )}
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </div>
      </div>
      <p className="citation-snippet">{citation.snippet}</p>
    </div>
  );
}
