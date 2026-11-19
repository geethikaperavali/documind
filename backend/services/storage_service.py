import os
from pathlib import Path
from typing import Tuple
from backend.config import settings
from backend.database import get_supabase_admin

# Local storage fallback directory
LOCAL_STORAGE_DIR = Path(__file__).resolve().parent.parent / "uploads"
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

class StorageService:
    """
    Manages document file storage in Supabase Storage bucket ('documents')
    with user-isolated paths: '<user_id>/<filename>', plus local fallback.
    """

    BUCKET_NAME = "documents"

    def upload_file(self, file_bytes: bytes, file_name: str, user_id: str, content_type: str) -> Tuple[str, str]:
        """
        Uploads file to Supabase Storage.
        Returns (storage_path, public_or_signed_url).
        """
        storage_path = f"{user_id}/{file_name}"

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

        # 2. Local fallback storage
        user_folder = LOCAL_STORAGE_DIR / user_id
        user_folder.mkdir(parents=True, exist_ok=True)
        local_file_path = user_folder / file_name
        with open(local_file_path, "wb") as f:
            f.write(file_bytes)

        return storage_path, f"/local-files/{user_id}/{file_name}"

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

        # Check local fallback
        parts = storage_path.split("/")
        filename = parts[-1]
        local_file_path = LOCAL_STORAGE_DIR / user_id / filename
        if local_file_path.exists():
            with open(local_file_path, "rb") as f:
                return f.read()

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

        # Try local fallback
        local_file_path = LOCAL_STORAGE_DIR / storage_path
        if local_file_path.exists():
            try:
                os.remove(local_file_path)
            except Exception:
                pass

        return True

storage_service = StorageService()
