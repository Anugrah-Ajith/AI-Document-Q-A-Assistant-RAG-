import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.schemas.document import (
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.vector_store import VectorStoreService

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

# Shared service instances
_pdf_service = PDFService()
_chunking_service = ChunkingService()
_embedding_service = EmbeddingService()
_vector_store = VectorStoreService()


def get_vector_store() -> VectorStoreService:
    return _vector_store


def get_embedding_service() -> EmbeddingService:
    return _embedding_service


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a PDF document",
    description="Extracts text page-by-page, divides it into overlapping chunks, computes embeddings, and stores them in ChromaDB."
)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to be ingested"),
    settings: Settings = Depends(get_settings),
    vector_store: VectorStoreService = Depends(get_vector_store),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> DocumentUploadResponse:
    # 1. Validate file extension
    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type for '{filename}'. Only PDF files (.pdf) are permitted."
        )

    # 2. Read bytes and enforce size constraint
    pdf_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(pdf_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # 3. Extract text page-by-page
    pages_data = _pdf_service.extract_pages_from_bytes(pdf_bytes=pdf_bytes, filename=filename)

    # 4. Generate deterministic chunk set with page citations
    document_id = str(uuid.uuid4())[:8]
    chunker = ChunkingService(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )
    chunks = chunker.chunk_pages(
        pages_data=pages_data,
        document_id=document_id,
        filename=filename
    )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not generate text chunks from '{filename}'."
        )

    # 5. Generate embeddings
    texts_to_embed = [c.content for c in chunks]
    embeddings = embedding_service.get_embeddings(texts_to_embed)

    # 6. Index in persistent vector store
    vector_store.add_chunks(chunks=chunks, embeddings=embeddings)

    return DocumentUploadResponse(
        document_id=document_id,
        filename=filename,
        total_pages=len(pages_data),
        total_chunks=len(chunks),
        message=f"Document '{filename}' successfully parsed, chunked into {len(chunks)} fragments, and indexed.",
        status="success"
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all indexed documents",
    description="Returns metadata, page counts, and chunk totals for all documents currently in the vector store."
)
async def list_documents(
    vector_store: VectorStoreService = Depends(get_vector_store)
) -> DocumentListResponse:
    docs = vector_store.list_documents()
    total_chunks = sum(d.total_chunks for d in docs)
    return DocumentListResponse(
        documents=docs,
        total_documents=len(docs),
        total_chunks=total_chunks
    )


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document by ID",
    description="Removes all vector embeddings and chunk metadata for the specified document ID."
)
async def delete_document(
    document_id: str,
    vector_store: VectorStoreService = Depends(get_vector_store)
) -> DeleteDocumentResponse:
    deleted_count = vector_store.delete_document(document_id)
    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' was not found in the vector store."
        )
    return DeleteDocumentResponse(
        document_id=document_id,
        deleted_chunks=deleted_count,
        message=f"Successfully deleted {deleted_count} chunks for document {document_id}."
    )
