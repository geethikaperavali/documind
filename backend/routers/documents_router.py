import uuid
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from backend.auth import get_current_user
from backend.database import get_supabase_admin
from backend.config import settings
from backend.services.document_processor import DocumentProcessor
from backend.services.embedding_service import embedding_service
from backend.services.storage_service import storage_service

router = APIRouter(prefix="/documents", tags=["Documents"])
processor = DocumentProcessor(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Uploads a document (PDF, DOCX, TXT), stores it in Supabase Storage,
    extracts text and pages, chunks the content, computes vector embeddings,
    and saves chunks to the database.
    """
    user_id = user["id"]
    filename = file.filename or "untitled_document"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type (.{ext}). Only PDF, DOCX, and TXT files are accepted."
        )

    # Read file bytes
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    if file_size > settings.MAX_FILE_SIZE_BYTES:
        max_mb = settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {max_mb} MB."
        )

    admin = get_supabase_admin()
    doc_id = str(uuid.uuid4())

    # 1. Upload original file to Supabase Storage
    try:
        content_type = file.content_type or "application/octet-stream"
        storage_path, file_url = storage_service.upload_file(
            file_bytes=file_bytes,
            file_name=f"{doc_id}_{filename}",
            user_id=user_id,
            content_type=content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document to storage: {str(e)}"
        )

    # 2. Insert initial document record in 'processing' status
    doc_record = {
        "id": doc_id,
        "user_id": user_id,
        "name": filename,
        "file_path": storage_path,
        "file_type": ext,
        "file_size": file_size,
        "status": "processing",
        "chunk_count": 0
    }

    try:
        admin.table("documents").insert(doc_record).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error creating document entry: {str(e)}"
        )

    # 3. Process text extraction & chunking
    try:
        pages_data = processor.extract_text_and_pages(file_bytes, ext)
        if not pages_data:
            admin.table("documents").update({
                "status": "failed",
                "error_message": "Could not extract any readable text from this document."
            }).eq("id", doc_id).execute()
            
            return {
                "id": doc_id,
                "name": filename,
                "status": "failed",
                "message": "No readable text extracted. Document marked as failed."
            }

        chunks = processor.chunk_document(pages_data)
        if not chunks:
            admin.table("documents").update({
                "status": "failed",
                "error_message": "Document content was too sparse to produce text chunks."
            }).eq("id", doc_id).execute()
            
            return {
                "id": doc_id,
                "name": filename,
                "status": "failed",
                "message": "Document produced 0 chunks."
            }

        # 4. Generate embeddings for all chunks in batch
        chunk_texts = [c["content"] for c in chunks]
        embeddings = embedding_service.generate_embeddings(chunk_texts)

        # 5. Prepare records for document_chunks table
        chunk_records = []
        for i, chunk in enumerate(chunks):
            chunk_records.append({
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "user_id": user_id,
                "content": chunk["content"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "embedding": embeddings[i],
                "metadata": {"file_type": ext, "filename": filename}
            })

        # Batch insert chunks (in batches of 50 to avoid payload limits)
        batch_size = 50
        for i in range(0, len(chunk_records), batch_size):
            batch = chunk_records[i : i + batch_size]
            admin.table("document_chunks").insert(batch).execute()

        # 6. Update document status to 'ready'
        admin.table("documents").update({
            "status": "ready",
            "chunk_count": len(chunks)
        }).eq("id", doc_id).execute()

        return {
            "id": doc_id,
            "name": filename,
            "file_type": ext,
            "file_size": file_size,
            "status": "ready",
            "chunk_count": len(chunks),
            "message": "Document successfully processed and indexed for RAG."
        }

    except Exception as e:
        err_msg = str(e)
        print(f"[DocumentsRouter] Processing error on doc {doc_id}: {err_msg}")
        admin.table("documents").update({
            "status": "failed",
            "error_message": err_msg
        }).eq("id", doc_id).execute()

        return {
            "id": doc_id,
            "name": filename,
            "status": "failed",
            "error": err_msg
        }

@router.get("")
async def list_documents(
    q: Optional[str] = Query(None, description="Search term for document name"),
    type: Optional[str] = Query(None, description="Filter by file type (pdf, docx, txt)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (ready, processing, failed)"),
    user: dict = Depends(get_current_user)
):
    """
    Returns list of all documents belonging to the authenticated user.
    Supports search query and filtering.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    try:
        query = admin.table("documents").select("*").eq("user_id", user_id)

        if type and type.lower() != "all":
            query = query.eq("file_type", type.lower())

        if status_filter and status_filter.lower() != "all":
            query = query.eq("status", status_filter.lower())

        if q and q.strip():
            query = query.ilike("name", f"%{q.strip()}%")

        res = query.order("created_at", desc=True).execute()
        return {"documents": res.data or []}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {str(e)}"
        )

@router.get("/{document_id}")
async def get_document_details(
    document_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Retrieves document details and its sample chunks.
    Validates user ownership.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    res = admin.table("documents").select("*").eq("id", document_id).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")

    doc = res.data[0]

    # Fetch chunks count and sample
    chunks_res = admin.table("document_chunks") \
        .select("id, page_number, chunk_index, content") \
        .eq("document_id", document_id) \
        .eq("user_id", user_id) \
        .order("chunk_index") \
        .limit(10) \
        .execute()

    return {
        "document": doc,
        "sample_chunks": chunks_res.data or []
    }

@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Returns the current processing status of a document.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    res = admin.table("documents").select("id, name, status, chunk_count, error_message").eq("id", document_id).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found.")

    return res.data[0]

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Permanently deletes a document, its associated storage file, and all chunks.
    Ensures strict user ownership.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    # 1. Fetch document to check ownership and get storage path
    res = admin.table("documents").select("*").eq("id", document_id).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found or permission denied.")

    doc = res.data[0]
    storage_path = doc.get("file_path")

    # 2. Delete storage file
    if storage_path:
        storage_service.delete_file(storage_path)

    # 3. Delete document row (cascades to document_chunks)
    try:
        admin.table("documents").delete().eq("id", document_id).eq("user_id", user_id).execute()
        return {"success": True, "message": f"Document '{doc.get('name')}' deleted successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document from database: {str(e)}"
        )
