from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata associated with an indexed chunk of text."""
    document_id: str = Field(description="Unique identifier for the document")
    filename: str = Field(description="Original filename of the source document")
    page: int = Field(ge=1, description="1-indexed source page number in the PDF")
    chunk_index: int = Field(ge=0, description="Sequential index of the chunk within the document")
    char_count: int = Field(ge=0, description="Length of the chunk in characters")


class DocumentChunk(BaseModel):
    """Represents an extracted and chunked piece of text ready for vector indexing."""
    id: str = Field(description="Deterministic chunk ID (e.g. docId_p1_c0)")
    content: str = Field(description="Raw text content of the chunk")
    metadata: ChunkMetadata = Field(description="Associated origin metadata")


class DocumentUploadResponse(BaseModel):
    """API response after successfully uploading and indexing a document."""
    document_id: str
    filename: str
    total_pages: int
    total_chunks: int
    message: str = "Document successfully ingested and indexed"
    status: str = "success"


class DocumentInfo(BaseModel):
    """Summary information for an indexed document."""
    document_id: str
    filename: str
    total_pages: int
    total_chunks: int
    uploaded_at: Optional[str] = None


class DocumentListResponse(BaseModel):
    """List of all documents indexed in the vector store."""
    documents: List[DocumentInfo]
    total_documents: int
    total_chunks: int


class DeleteDocumentResponse(BaseModel):
    """Response returned upon deleting a document and its vectors."""
    document_id: str
    deleted_chunks: int
    message: str = "Document and associated vectors successfully removed"
    status: str = "success"
