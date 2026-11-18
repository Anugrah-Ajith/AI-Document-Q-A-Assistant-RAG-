import re
from typing import List, Dict, Any
from app.schemas.document import DocumentChunk, ChunkMetadata


class ChunkingService:
    """
    Splits document text into overlapping chunks while preserving page citations
    and structural coherence (paragraphs and sentences).
    """

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 120):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative.")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly smaller than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text_into_chunks(self, text: str) -> List[str]:
        """
        Splits a single text string into overlapping chunks respecting sentence
        and word boundaries whenever feasible.
        """
        text = text.strip()
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.chunk_overlap
        chunks: List[str] = []
        start = 0
        total_len = len(text)

        while start < total_len:
            end = min(start + self.chunk_size, total_len)
            candidate = text[start:end]

            # If not at the very end of text, attempt to break at a natural boundary
            if end < total_len:
                # Look for paragraph break, then sentence terminator, then whitespace
                break_found = -1
                search_region = candidate[max(0, len(candidate) - int(self.chunk_overlap * 1.5)):]
                
                # Try finding double newline
                double_nl = candidate.rfind("\n\n")
                if double_nl > int(self.chunk_size * 0.4):
                    break_found = double_nl + 2
                else:
                    # Try sentence punctuation: period, exclamation, question mark followed by space or newline
                    matches = list(re.finditer(r"[\.\?\!]\s+", candidate))
                    if matches:
                        last_match = matches[-1]
                        if last_match.end() > int(self.chunk_size * 0.4):
                            break_found = last_match.end()
                    
                    if break_found == -1:
                        # Try space boundary
                        last_space = candidate.rfind(" ")
                        if last_space > int(self.chunk_size * 0.4):
                            break_found = last_space + 1

                if break_found > 0:
                    end = start + break_found
                    candidate = text[start:end]

            chunk_str = candidate.strip()
            if chunk_str:
                chunks.append(chunk_str)

            # Move start pointer forward
            if end >= total_len:
                break
            
            # Next start accounts for overlap
            next_start = end - self.chunk_overlap
            if next_start <= start:
                next_start = start + step
            start = next_start

        return chunks

    def chunk_pages(
        self,
        pages_data: List[Dict[str, Any]],
        document_id: str,
        filename: str
    ) -> List[DocumentChunk]:
        """
        Chunks page-delimited document data and attaches strict page citations.

        Args:
            pages_data: List of dicts with 'page' (int) and 'text' (str).
            document_id: Unique document identifier.
            filename: Name of the uploaded file.

        Returns:
            List[DocumentChunk]: Ready-to-embed chunk objects with full metadata.
        """
        document_chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page_item in pages_data:
            page_num = page_item["page"]
            page_text = page_item.get("text", "").strip()

            if not page_text:
                continue

            page_chunks = self.split_text_into_chunks(page_text)

            for local_idx, chunk_text in enumerate(page_chunks):
                chunk_id = f"{document_id}_p{page_num}_c{global_chunk_idx}"
                metadata = ChunkMetadata(
                    document_id=document_id,
                    filename=filename,
                    page=page_num,
                    chunk_index=global_chunk_idx,
                    char_count=len(chunk_text),
                )
                document_chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        content=chunk_text,
                        metadata=metadata,
                    )
                )
                global_chunk_idx += 1

        return document_chunks
