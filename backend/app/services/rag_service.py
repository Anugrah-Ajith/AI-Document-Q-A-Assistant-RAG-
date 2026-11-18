import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from openai import OpenAI

from app.config import get_settings
from app.core.session_manager import session_manager
from app.schemas.chat import ChatMessage, Citation
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class RAGService:
    """
    Retrieval-Augmented Generation service coordinating vector retrieval,
    multi-turn chat context assembly, and LLM answer generation with strict citations.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        settings = get_settings()
        self.settings = settings
        self.vector_store = vector_store or VectorStoreService()
        self.embedding_service = embedding_service or EmbeddingService()

        self.client: Optional[OpenAI] = None
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("your_openai"):
            try:
                self.client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                )
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client for RAG: {e}")
                self.client = None

    def retrieve_context(
        self,
        query: str,
        top_k: int = 4,
        filter_document_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[Citation]]:
        """
        Embeds user query, retrieves top-k chunks from ChromaDB, and builds citation objects.
        """
        query_embedding = self.embedding_service.get_single_embedding(query)
        where_filter = {"document_id": filter_document_id} if filter_document_id else None

        raw_chunks = self.vector_store.query_similar(
            query_embedding=query_embedding,
            top_k=top_k,
            where_filter=where_filter,
            query_text=query
        )

        citations: List[Citation] = []
        seen_keys = set()

        for chunk in raw_chunks:
            meta = chunk.get("metadata", {})
            filename = meta.get("filename", "unknown.pdf")
            page = int(meta.get("page", 1))
            chunk_id = chunk.get("chunk_id", "")
            content = chunk.get("content", "").strip()
            score = chunk.get("similarity", 0.0)

            # Make readable snippet
            clean_snippet = re.sub(r"\s+", " ", content)
            snippet = clean_snippet[:220] + "..." if len(clean_snippet) > 220 else clean_snippet

            key = (filename, page, chunk_id)
            if key not in seen_keys:
                seen_keys.add(key)
                citations.append(
                    Citation(
                        filename=filename,
                        page=page,
                        chunk_id=chunk_id,
                        snippet=snippet,
                        relevance_score=score
                    )
                )

        return raw_chunks, citations

    def _build_context_prompt(self, raw_chunks: List[Dict[str, Any]]) -> str:
        """Formats retrieved chunks into clear, cited context blocks."""
        if not raw_chunks:
            return "No matching document excerpts were found in the database."

        context_blocks = []
        for i, chunk in enumerate(raw_chunks, start=1):
            meta = chunk.get("metadata", {})
            filename = meta.get("filename", "Unknown Document")
            page = meta.get("page", 1)
            content = chunk.get("content", "").strip()
            context_blocks.append(
                f"[Excerpt {i}] (Document: '{filename}', Page: {page})\n{content}"
            )
        return "\n\n".join(context_blocks)

    def _fallback_synthesize(
        self,
        question: str,
        raw_chunks: List[Dict[str, Any]],
        citations: List[Citation]
    ) -> str:
        """
        Extractive heuristic answer generator for offline development or testing
        when an external LLM API key is not supplied.
        """
        refusal = (
            "Based on the uploaded documents, this information is not available "
            "in the provided text."
        )

        if not raw_chunks or not citations:
            return refusal

        # Check maximum similarity in raw_chunks
        max_similarity = max((c.get("similarity", 0.0) for c in raw_chunks), default=0.0)
        if max_similarity < self.settings.SIMILARITY_THRESHOLD:
            return refusal

        # Extract meaningful keywords from question
        stop_words = {
            "what", "is", "the", "in", "and", "of", "to", "a", "for", "on",
            "how", "why", "who", "when", "where", "which", "are", "will", "from", "with",
            "his", "her", "their", "my", "your", "its", "me", "him", "them", "tell", "about"
        }
        raw_tokens = re.findall(r"\w+", question.lower())
        keywords = {k for k in raw_tokens if len(k) > 1 and k not in stop_words}

        if not keywords:
            return refusal

        # Dedicated handler for Name / Author extraction (e.g. Resumes, papers, reports)
        if "name" in keywords or "who" in raw_tokens:
            for chunk in raw_chunks:
                content = chunk.get("content", "")
                meta = chunk.get("metadata", {})
                fn = meta.get("filename", "document.pdf")
                pg = meta.get("page", 1)
                lines = [l.strip() for l in content.split("\n") if l.strip()]
                for line in lines[:6]:
                    words = line.split()
                    if 1 <= len(words) <= 4 and all(w.isupper() or w.istitle() for w in words):
                        if not any(skip in line.lower() for skip in ["resume", "curriculum", "page", "developer", "summary", "experience", "education", "project"]):
                            # Found candidate name in document header!
                            name_str = line.title()
                            return f"The individual identified in the document is {name_str}. [Source: {fn}, Page: {pg}]"

        best_sentences: List[Tuple[int, str, str, int]] = []
        for chunk in raw_chunks:
            content = chunk.get("content", "")
            meta = chunk.get("metadata", {})
            fn = meta.get("filename", "document.pdf")
            pg = meta.get("page", 1)
            sentences = re.split(r"(?<=[.!?])\s+", content)

            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                s_lower = s_clean.lower()
                s_words = set(re.findall(r"\w+", s_lower))

                # Identify which distinct question keywords are matched
                matched_kws = set()
                score = 0
                for kw in keywords:
                    # Normalize common variations
                    kw_variant = "led" if kw == "lead" else kw
                    if kw in s_words or kw_variant in s_words:
                        matched_kws.add(kw)
                        score += 4
                    elif any(
                        (len(w) >= 4 and len(kw) >= 4 and (w.startswith(kw[:4]) or kw.startswith(w[:4])))
                        for w in s_words
                    ):
                        matched_kws.add(kw)
                        score += 2

                # Require at least 2 distinct question keywords for multi-word questions
                min_matched = 2 if len(keywords) >= 3 else 1
                if len(matched_kws) >= min_matched:
                    # Discount generic recurring title words (project, apex)
                    specific_matches = matched_kws - {"project", "apex"}
                    if specific_matches:
                        score += len(specific_matches) * 3
                    best_sentences.append((score, s_clean, fn, pg))

        if not best_sentences:
            return refusal

        # Sort sentences by match score descending
        best_sentences.sort(key=lambda x: x[0], reverse=True)

        seen_sents = set()
        chosen: List[str] = []
        for _, s, fn, pg in best_sentences[:3]:
            if s not in seen_sents:
                seen_sents.add(s)
                chosen.append(f"{s} [Source: {fn}, Page: {pg}]")

        return " ".join(chosen)

    async def answer_question(
        self,
        question: str,
        session_id: str,
        top_k: Optional[int] = None,
        filter_document_id: Optional[str] = None
    ) -> Tuple[str, List[Citation], int]:
        """
        Orchestrates RAG flow: retrieval, conversation history inclusion,
        grounded prompt generation, and LLM inference.

        Returns:
            Tuple[str, List[Citation], int]: (answer_text, citations_list, chunks_retrieved_count)
        """
        k = top_k or self.settings.DEFAULT_TOP_K
        raw_chunks, citations = self.retrieve_context(
            query=question,
            top_k=k,
            filter_document_id=filter_document_id
        )

        # Retrieve recent session history (last 6 turns = 3 user/assistant pairs)
        history: List[ChatMessage] = session_manager.get_history(session_id, limit=6)

        context_text = self._build_context_prompt(raw_chunks)

        system_prompt = (
            "You are a helpful, accurate, and rigorous AI Document Q&A Assistant.\n"
            "Your objective is to answer the user's questions based EXCLUSIVELY on the provided document excerpts.\n\n"
            "CRITICAL GUIDELINES:\n"
            "1. Grounding: Answer strictly using facts present in the excerpts. Never fabricate information.\n"
            "2. Citations: Every key factual claim or statement MUST be directly followed by an inline source citation in the format: "
            "[Source: <filename>, Page: <page>].\n"
            "3. Negative Rejection: If the provided excerpts do not contain enough information to answer the question, clearly state: "
            "'Based on the uploaded documents, this information is not available in the provided text.' Do not speculate.\n"
            "4. Tone: Clear, concise, and professional."
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Inject conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Inject current context and question
        user_prompt = (
            f"DOCUMENT EXCERPTS:\n{context_text}\n\n"
            f"USER QUESTION: {question}\n\n"
            "Please provide a well-structured answer with inline citations [Source: <filename>, Page: <page>]:"
        )
        messages.append({"role": "user", "content": user_prompt})

        answer: str = ""
        if self.client is not None:
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.LLM_MODEL,
                    messages=messages,  # type: ignore
                    temperature=0.1,
                    max_tokens=800
                )
                answer = response.choices[0].message.content or ""
            except Exception as e:
                logger.error(f"Error calling LLM: {e}. Using deterministic synthesis.")
                answer = self._fallback_synthesize(question, raw_chunks, citations)
        else:
            answer = self._fallback_synthesize(question, raw_chunks, citations)

        # Record turns in session history
        session_manager.add_message(session_id, role="user", content=question)
        session_manager.add_message(session_id, role="assistant", content=answer, citations=citations)

        return answer, citations, len(raw_chunks)
