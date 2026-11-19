import io
import re
from typing import List, Dict, Any

# Try importing pymupdf (formerly fitz), fallback to pypdf if not yet installed
try:
    import pymupdf as fitz  # PyMuPDF
    HAVE_PYMUPDF = True
except ImportError:
    try:
        import fitz
        HAVE_PYMUPDF = True
    except ImportError:
        HAVE_PYMUPDF = False

try:
    import pypdf
    HAVE_PYPDF = True
except ImportError:
    HAVE_PYPDF = False

try:
    import docx
    HAVE_DOCX = True
except ImportError:
    HAVE_DOCX = False


class DocumentProcessor:
    """
    Extracts text and page structure from PDF, DOCX, and TXT files,
    and performs semantic chunking with page number preservation for citations.
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
        pages_content = []

        if file_type == "pdf":
            pages_content = self._extract_pdf(file_bytes)
        elif file_type in ("docx", "doc"):
            pages_content = self._extract_docx(file_bytes)
        elif file_type == "txt":
            pages_content = self._extract_txt(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: .{file_type}. Supported types: PDF, DOCX, TXT.")

        return pages_content

    def _extract_pdf(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        pages = []
        if HAVE_PYMUPDF:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text").strip()
                if text:
                    pages.append({"page_number": page_num + 1, "text": text})
            doc.close()
        elif HAVE_PYPDF:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for i, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append({"page_number": i + 1, "text": text})
        else:
            raise RuntimeError("Neither PyMuPDF nor pypdf is installed to extract PDF text.")

        return pages

    def _extract_docx(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        if not HAVE_DOCX:
            raise RuntimeError("python-docx is not installed to extract DOCX text.")

        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        # Word documents do not have fixed physical pages in the XML;
        # We group every 4-5 paragraphs or ~2500 chars into simulated "pages/sections" for citation.
        pages = []
        current_page_text = []
        current_char_count = 0
        page_num = 1

        for p in paragraphs:
            current_page_text.append(p)
            current_char_count += len(p)
            if current_char_count >= 2000:
                pages.append({
                    "page_number": page_num,
                    "text": "\n\n".join(current_page_text)
                })
                current_page_text = []
                current_char_count = 0
                page_num += 1

        if current_page_text:
            pages.append({
                "page_number": page_num,
                "text": "\n\n".join(current_page_text)
            })

        return pages

    def _extract_txt(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        # Try UTF-8 decoding, fallback to latin-1
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")

        text = text.strip()
        if not text:
            return []

        # Divide plain text into ~2000 character logical pages
        pages = []
        page_size = 2000
        total_len = len(text)
        page_num = 1
        start = 0

        while start < total_len:
            end = min(start + page_size, total_len)
            chunk = text[start:end].strip()
            if chunk:
                pages.append({"page_number": page_num, "text": chunk})
            start = end
            page_num += 1

        return pages

    def chunk_document(self, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits extracted pages into overlapping chunks while preserving page number.
        Returns a list of dicts:
        [
            {
                "content": str,
                "page_number": int,
                "chunk_index": int
            }
        ]
        """
        all_chunks = []
        global_chunk_idx = 0

        for page in pages_data:
            page_num = page["page_number"]
            page_text = page["text"]

            page_chunks = self._chunk_text(page_text)
            for chunk_str in page_chunks:
                if len(chunk_str.strip()) < 20:
                    continue  # skip empty or trivial chunks
                all_chunks.append({
                    "content": chunk_str.strip(),
                    "page_number": page_num,
                    "chunk_index": global_chunk_idx
                })
                global_chunk_idx += 1

        return all_chunks

    def _chunk_text(self, text: str) -> List[str]:
        """
        Splits text into chunks of roughly `self.chunk_size` characters,
        preferring natural sentence/paragraph boundaries with `self.chunk_overlap`.
        """
        # Normalize whitespace
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)

        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    # Create overlap from end of current_chunk
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                    current_chunk = f"{overlap_text}\n\n{para}".strip()
                else:
                    # Paragraph itself is larger than chunk_size, split by sentences or characters
                    sentences = re.split(r'(?<=[.!?]) +', para)
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) <= self.chunk_size:
                            sub_chunk = f"{sub_chunk} {s}".strip()
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = s
                    if sub_chunk:
                        current_chunk = sub_chunk

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
