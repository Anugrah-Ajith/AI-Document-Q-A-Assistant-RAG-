import io
import re
from typing import List, Dict, Any
from pypdf import PdfReader
from fastapi import HTTPException, status


class PDFExtractionError(Exception):
    """Custom exception raised when PDF text extraction fails."""
    pass


class PDFService:
    """Service responsible for parsing PDFs and extracting page-delimited text."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Sanitizes raw extracted text by removing control characters and excessive whitespaces."""
        if not text:
            return ""
        # Remove null bytes and non-printable characters except standard whitespace
        text = text.replace("\x00", " ")
        # Normalize multiple horizontal whitespaces
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize excessive newlines (more than 2 consecutive newlines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def extract_pages_from_bytes(self, pdf_bytes: bytes, filename: str = "document.pdf") -> List[Dict[str, Any]]:
        """
        Parses a PDF byte stream and returns a list of dictionaries containing
        the 1-indexed page number and extracted text.

        Returns:
            List[Dict[str, Any]]: [{"page": 1, "text": "...", "char_count": 120}, ...]
        """
        if not pdf_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The uploaded file '{filename}' is empty."
            )

        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse PDF '{filename}': Invalid or corrupted PDF file. ({str(e)})"
            )

        if reader.is_encrypted:
            try:
                # Attempt empty password decryption
                reader.decrypt("")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The file '{filename}' is password-protected and cannot be read."
                )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF '{filename}' contains 0 pages."
            )

        pages_data: List[Dict[str, Any]] = []

        for index, page in enumerate(reader.pages):
            page_number = index + 1
            try:
                extracted = page.extract_text() or ""
            except Exception as e:
                extracted = f"[Text extraction warning on page {page_number}: {str(e)}]"

            cleaned = self.clean_text(extracted)
            pages_data.append({
                "page": page_number,
                "text": cleaned,
                "char_count": len(cleaned)
            })

        # Check if the entire document was blank/unextractable (e.g. scanned image without OCR)
        total_text_length = sum(p["char_count"] for p in pages_data)
        if total_text_length == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"No text could be extracted from '{filename}'. "
                    "The document may contain only scanned images or raster graphics without a selectable text layer."
                )
            )

        return pages_data
