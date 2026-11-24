import os
import re
from pathlib import Path
from typing import Tuple
from backend.config import settings
from backend.database import get_supabase_admin

# Local storage fallback directory
LOCAL_STORAGE_DIR = (Path(__file__).resolve().parent.parent / "uploads").resolve()
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

class StorageService:
    """
    Manages document file storage in Supabase Storage bucket ('documents')
    with user-isolated paths: '<user_id>/<filename>', plus local fallback.
    Enforces strict path traversal defenses on all storage operations.
    """

    BUCKET_NAME = "documents"

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Strips directory components and replaces unsafe characters.
        Enforces strict alphanumeric, dot, underscore, hyphen whitelist.
        Handles URL-encoded sequences and null-byte injection.
        """
        import urllib.parse
        # Decode any URL-encoded traversal payloads (%2e%2e%2f -> ../)
        unquoted = urllib.parse.unquote(filename or "file")
        # Strip null bytes and control characters
        cleaned_str = unquoted.replace("\x00", "").strip()
        base = os.path.basename(cleaned_str)
        # Whitelist alphanumeric, dot, underscore, hyphen
        clean = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
        # Prevent hidden files and leading/trailing dots or spaces
        safe = re.sub(r"\.{2,}", "_", clean).lstrip(".").strip()
        return safe or "unnamed_document"

    def upload_file(self, file_bytes: bytes, file_name: str, user_id: str, content_type: str) -> Tuple[str, str]:
        """
        Uploads file to Supabase Storage with local fallback.
        Returns (storage_path, public_or_signed_url).
        """
        clean_file_name = self.sanitize_filename(file_name)
        clean_user_id = self.sanitize_filename(user_id)
        storage_path = f"{clean_user_id}/{clean_file_name}"

        # 1. Try uploading to Supabase Storage
        try:
            admin = get_supabase_admin()
            # Ensure bucket exists
            try:
                admin.storage.get_bucket(self.BUCKET_NAME)
            except Exception:
                try:
                    admin.storage.create_bucket(self.BUCKET_NAME, options={"public": False})
                except Exception:
                    pass

            # Upload or upsert
            admin.storage.from_(self.BUCKET_NAME).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            # Create a signed URL for reading (valid for 1 hour)
            url_res = admin.storage.from_(self.BUCKET_NAME).create_signed_url(storage_path, 3600)
            file_url = url_res.get("signedURL", "") if isinstance(url_res, dict) else ""
            return storage_path, file_url
        except Exception as e:
            print(f"[StorageService] Supabase Storage upload error ({e}). Using local fallback.")

        # 2. Local fallback storage with strict directory containment check (genuine boundary check)
        user_folder = (LOCAL_STORAGE_DIR / clean_user_id).resolve()
        user_folder.mkdir(parents=True, exist_ok=True)
        local_file_path = (user_folder / clean_file_name).resolve()

        try:
            # Genuine filesystem hierarchy containment verification
            rel_path = local_file_path.relative_to(user_folder)
            if not rel_path.parts or local_file_path == user_folder:
                raise ValueError("Target path must be a file inside user directory")
        except ValueError:
            raise ValueError(f"Path traversal security exception for file: {file_name}")

        with open(local_file_path, "wb") as f:
            f.write(file_bytes)

        return storage_path, f"/local-files/{clean_user_id}/{clean_file_name}"

    def download_file(self, storage_path: str, user_id: str) -> bytes:
        """
        Downloads file bytes from Supabase Storage or local fallback.
        """
        try:
            admin = get_supabase_admin()
            file_bytes = admin.storage.from_(self.BUCKET_NAME).download(storage_path)
            if file_bytes:
                return file_bytes
        except Exception as e:
            print(f"[StorageService] Supabase download error ({e}). Checking local fallback.")

        # Check local fallback with strict containment
        parts = storage_path.replace("\\", "/").split("/")
        clean_user_id = self.sanitize_filename(parts[0] if len(parts) > 1 else user_id)
        clean_filename = self.sanitize_filename(parts[-1])

        user_folder = (LOCAL_STORAGE_DIR / clean_user_id).resolve()
        local_file_path = (user_folder / clean_filename).resolve()

        try:
            local_file_path.relative_to(user_folder)
            if local_file_path.exists() and local_file_path.is_file():
                with open(local_file_path, "rb") as f:
                    return f.read()
        except ValueError:
            pass

        raise FileNotFoundError(f"File not found at storage path: {storage_path}")

    def delete_file(self, storage_path: str) -> bool:
        """
        Deletes file from Supabase Storage and local fallback.
        """
        # Try Supabase Storage
        try:
            admin = get_supabase_admin()
            admin.storage.from_(self.BUCKET_NAME).remove([storage_path])
        except Exception as e:
            print(f"[StorageService] Supabase delete warning: {e}")

        # Try local fallback with containment validation
        try:
            parts = storage_path.replace("\\", "/").split("/")
            if len(parts) >= 2:
                user_folder = (LOCAL_STORAGE_DIR / self.sanitize_filename(parts[0])).resolve()
                local_file_path = (user_folder / self.sanitize_filename(parts[-1])).resolve()
                local_file_path.relative_to(user_folder)
                if local_file_path.exists() and local_file_path.is_file():
                    os.remove(local_file_path)
        except (ValueError, Exception) as e:
            print(f"[StorageService] Local delete warning: {e}")

        return True

storage_service = StorageService()
