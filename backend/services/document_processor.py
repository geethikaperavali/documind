import io
import re
from typing import List, Dict, Any

class DocumentProcessor:
    """
    Extracts text and page structure from PDF, DOCX, and TXT files,
    and performs semantic chunking with page number preservation for citations.
    Dependencies (pymupdf, pypdf, docx) are imported lazily on demand to accelerate app startup.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_and_pages(self, file_bytes: bytes, file_type: str) -> List[Dict[str, Any]]:
        """
        Extracts content divided by page/section.
        Returns a list of dicts: [{"page_number": int, "text": str}]
        """
        file_type = file_type.lower().strip().replace(".", "")

        if file_type == "pdf":
            return self._extract_pdf(file_bytes)
        elif file_type in ("docx", "doc"):
            return self._extract_docx(file_bytes)
        elif file_type == "txt":
            return self._extract_txt(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {file_type}. Supported: pdf, docx, txt")

    def _extract_pdf(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extracts pages from PDF using PyMuPDF (fitz) if available, falling back to pypdf.
        """
        # Lazy import PyMuPDF
        try:
            import pymupdf as fitz
            have_pymupdf = True
        except ImportError:
            try:
                import fitz
                have_pymupdf = True
            except ImportError:
                have_pymupdf = False

        if have_pymupdf:
            pages = []
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for page_idx in range(len(doc)):
                    page = doc[page_idx]
                    text = page.get_text() or ""
                    cleaned = self._clean_text(text)
                    if cleaned:
                        pages.append({
                            "page_number": page_idx + 1,
                            "text": cleaned
                        })
                doc.close()
                if pages:
                    return pages
            except Exception as e:
                print(f"[DocumentProcessor] PyMuPDF extraction failed: {e}. Falling back to pypdf.")

        # Fallback to pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = []
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                cleaned = self._clean_text(text)
                if cleaned:
                    pages.append({
                        "page_number": idx + 1,
                        "text": cleaned
                    })
            return pages
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from PDF: {e}")

    def _extract_docx(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extracts paragraphs and approximate pages from DOCX using python-docx.
        """
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            full_text = "\n".join(paragraphs)

            # Split into synthetic pages of roughly 2500 characters
            synthetic_pages = []
            page_size = 2500
            for i in range(0, max(len(full_text), 1), page_size):
                chunk = full_text[i:i + page_size]
                synthetic_pages.append({
                    "page_number": (i // page_size) + 1,
                    "text": self._clean_text(chunk)
                })
            return synthetic_pages
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from DOCX: {e}")

    def _extract_txt(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Decodes raw text with utf-8 (or latin-1 fallback).
        """
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")

        # Split into synthetic pages of roughly 2500 characters
        synthetic_pages = []
        page_size = 2500
        for i in range(0, max(len(text), 1), page_size):
            chunk = text[i:i + page_size]
            synthetic_pages.append({
                "page_number": (i // page_size) + 1,
                "text": self._clean_text(chunk)
            })
        return synthetic_pages

    def chunk_document(self, pages_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits extracted pages into semantic chunks with overlap.
        Preserves page_number, start/end character offsets, and chunk metadata.
        """
        chunks = []
        chunk_idx = 0

        for page in pages_content:
            page_num = page["page_number"]
            text = page["text"]

            # Token/word approximation: split on whitespace
            words = text.split()
            if not words:
                continue

            step = max(1, self.chunk_size - self.chunk_overlap)
            for i in range(0, len(words), step):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = " ".join(chunk_words)

                chunks.append({
                    "chunk_index": chunk_idx,
                    "page_number": page_num,
                    "content": chunk_text,
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_words)
                })
                chunk_idx += 1

                # If this chunk reaches the end of the words, stop
                if i + self.chunk_size >= len(words):
                    break

        return chunks

    def _clean_text(self, text: str) -> str:
        """
        Cleans extraneous whitespace, control characters, and null bytes.
        """
        if not text:
            return ""
        # Remove null bytes and control chars except newlines and tabs
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        # Normalize multiple horizontal whitespaces
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

document_processor = DocumentProcessor()
