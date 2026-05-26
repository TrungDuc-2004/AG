"""Legacy placeholder.

The project storage has been migrated from MinIO to Google Drive. Keep this
module only so older imports fail with a clear message instead of an ImportError.
"""


def get_minio_client():
    raise RuntimeError("MinIO has been replaced by Google Drive storage. Use app.services.storage_service.StorageService.")


def ensure_bucket_exists() -> None:
    raise RuntimeError("MinIO has been replaced by Google Drive storage. Configure Google Drive instead.")
