import logging
import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import get_settings
from app.schemas.document import DocumentChunk, DocumentInfo

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Manages persistent vector indexing, metadata filtering, and top-k retrieval via ChromaDB."""

    def __init__(self, persist_dir: Optional[str] = None, collection_name: Optional[str] = None):
        settings = get_settings()
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME

        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> int:
        """
        Indexes chunks into ChromaDB with vector embeddings and full page metadata.

        Returns:
            int: Number of chunks successfully inserted.
        """
        if not chunks:
            return 0

        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata.model_dump() for chunk in chunks]

        # ChromaDB accepts batch upsert
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Indexed {len(chunks)} chunks into collection '{self.collection_name}'.")
        return len(chunks)

    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        where_filter: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k closest chunks based on hybrid dense and lexical/intent scoring.

        Returns:
            List[Dict[str, Any]]: List of matching results with chunk content, metadata, and score.
        """
        import re
        total_items = self.collection.count()
        if total_items == 0:
            return []

        # Retrieve a broader pool of candidates for hybrid re-ranking
        candidate_k = min(max(top_k * 4, 15), total_items)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=candidate_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        formatted_matches: List[Dict[str, Any]] = []
        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
            return formatted_matches

        ids = results["ids"][0]
        docs = results["documents"][0] if results.get("documents") else []
        metas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        # Prepare lexical query tokens
        query_words = set()
        name_intent = False
        if query_text:
            stop_words = {
                "what", "is", "the", "in", "and", "of", "to", "a", "for", "on",
                "how", "why", "who", "when", "where", "which", "are", "will", "from", "with",
                "his", "her", "their", "my", "your", "its", "me", "him", "them", "tell", "about"
            }
            raw_tokens = re.findall(r"\w+", query_text.lower())
            query_words = {w for w in raw_tokens if len(w) > 1 and w not in stop_words}
            name_intent = any(w in query_words for w in ["name", "author", "candidate", "developer", "person", "engineer"]) or "who" in raw_tokens

        scored_candidates = []
        for idx in range(len(ids)):
            dist = distances[idx] if idx < len(distances) else 1.0
            vec_sim = max(0.0, 1.0 - float(dist))
            doc_text = docs[idx] if idx < len(docs) else ""
            meta = metas[idx] if idx < len(metas) else {}
            doc_lower = doc_text.lower()
            doc_words = set(re.findall(r"\w+", doc_lower))

            # Keyword match ratio
            kw_score = 0.0
            if query_words:
                kw_matches = 0
                for kw in query_words:
                    if kw in doc_words:
                        kw_matches += 1
                    elif any(w.startswith(kw[:4]) or kw.startswith(w[:4]) for w in doc_words if len(w) >= 4 and len(kw) >= 4):
                        kw_matches += 0.5
                kw_score = kw_matches / max(len(query_words), 1)

            # Header / Name / Identity boost
            header_boost = 0.0
            if name_intent:
                if any(signal in doc_lower for signal in ["email", "@", "phone", "+91", "summary", "objective", "curriculum vitae", "resume"]):
                    header_boost += 0.35
                if meta.get("chunk_index", -1) == 0:
                    header_boost += 0.25

            # Hybrid score
            combined_score = (0.5 * vec_sim) + (0.35 * kw_score) + header_boost
            final_similarity = round(max(vec_sim, min(1.0, combined_score)), 4)

            scored_candidates.append({
                "chunk_id": ids[idx],
                "content": doc_text,
                "metadata": meta,
                "distance": float(dist),
                "similarity": final_similarity,
                "combined_rank_score": combined_score
            })

        # Sort by hybrid combined rank score descending
        scored_candidates.sort(key=lambda x: x["combined_rank_score"], reverse=True)
        return scored_candidates[:top_k]

    def list_documents(self) -> List[DocumentInfo]:
        """Scans indexed chunks and aggregates document level metrics."""
        count = self.collection.count()
        if count == 0:
            return []

        all_records = self.collection.get(include=["metadatas"])
        metas = all_records.get("metadatas", [])

        docs_summary: Dict[str, Dict[str, Any]] = {}
        for m in metas:
            if not m:
                continue
            doc_id = m.get("document_id", "unknown")
            filename = m.get("filename", "unknown")
            page = m.get("page", 1)

            if doc_id not in docs_summary:
                docs_summary[doc_id] = {
                    "document_id": doc_id,
                    "filename": filename,
                    "pages": set(),
                    "chunk_count": 0
                }

            docs_summary[doc_id]["pages"].add(page)
            docs_summary[doc_id]["chunk_count"] += 1

        result: List[DocumentInfo] = []
        for doc_id, data in docs_summary.items():
            result.append(
                DocumentInfo(
                    document_id=doc_id,
                    filename=data["filename"],
                    total_pages=len(data["pages"]),
                    total_chunks=data["chunk_count"],
                    uploaded_at=None
                )
            )

        return result

    def delete_document(self, document_id: str) -> int:
        """Deletes all chunks associated with a specific document."""
        existing = self.collection.get(where={"document_id": document_id})
        ids_to_delete = existing.get("ids", [])
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """Returns collection statistics."""
        return {
            "collection_name": self.collection_name,
            "total_chunks": self.collection.count(),
            "persist_dir": self.persist_dir
        }

    def reset(self) -> None:
        """Clears all records from the collection."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
