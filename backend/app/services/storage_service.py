import io
import os
import tempfile
from typing import Any

from fastapi import UploadFile
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from app.core.config import settings
from app.core.drive_client import get_drive_service


GOOGLE_DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class StorageService:
    """Google Drive implementation for file storage.

    MongoDB keeps the metadata; Google Drive stores the binary file. The old
    MinIO objectKey is preserved as a logical path so the rest of the app can
    continue using filePath/storage.objectKey.
    """

    def __init__(self) -> None:
        if settings.STORAGE_PROVIDER != "google_drive":
            raise RuntimeError(
                "This build is configured for Google Drive storage. "
                "Set STORAGE_PROVIDER=google_drive."
            )
        self.root_folder_id = settings.GOOGLE_DRIVE_ROOT_FOLDER_ID.strip()
        if not self.root_folder_id or self.root_folder_id.startswith("put_your_"):
            raise RuntimeError(
                "Missing GOOGLE_DRIVE_ROOT_FOLDER_ID. Create/share a Drive folder and put its ID in .env."
            )
        self.client = get_drive_service()

    async def upload_file(self, *, file: UploadFile, object_key: str) -> dict[str, Any]:
        """Upload FastAPI UploadFile to Google Drive and return StorageInfo fields."""
        await file.seek(0)
        size = 0
        temp_path: str | None = None
        media = None

        try:
            suffix = os.path.splitext(file.filename or "uploaded-file")[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                temp_path = tmp.name
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    tmp.write(chunk)

            object_parts = [part for part in object_key.strip("/").split("/") if part]
            if not object_parts:
                raise ValueError("object_key must not be empty")

            filename = object_parts[-1]
            folder_parts = object_parts[:-1]
            parent_folder_id = self.ensure_drive_path(folder_parts)

            media = MediaFileUpload(
                temp_path,
                mimetype=file.content_type or "application/octet-stream",
                resumable=True,
            )
            metadata = {
                "name": filename,
                "parents": [parent_folder_id],
            }

            existing_file_id = self.find_file_in_folder(filename=filename, parent_id=parent_folder_id)
            if existing_file_id:
                created = (
                    self.client.files()
                    .update(
                        fileId=existing_file_id,
                        body={"name": filename},
                        media_body=media,
                        fields="id,name,mimeType,size,webViewLink,webContentLink,parents",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
            else:
                created = (
                    self.client.files()
                    .create(
                        body=metadata,
                        media_body=media,
                        fields="id,name,mimeType,size,webViewLink,webContentLink,parents",
                        supportsAllDrives=True,
                    )
                    .execute()
                )

            if settings.GOOGLE_DRIVE_MAKE_PUBLIC:
                self.make_file_public(created["id"])
                created = (
                    self.client.files()
                    .get(
                        fileId=created["id"],
                        fields="id,name,mimeType,size,webViewLink,webContentLink,parents",
                        supportsAllDrives=True,
                    )
                    .execute()
                )

            return {
                "provider": "google_drive",
                "objectKey": object_key,
                "rootFolderId": self.root_folder_id,
                "folderId": parent_folder_id,
                "fileId": created.get("id"),
                "webViewLink": created.get("webViewLink"),
                "webContentLink": created.get("webContentLink"),
                "mimeType": created.get("mimeType") or file.content_type,
                "sizeBytes": int(created.get("size") or size),
            }
        except HttpError as exc:
            self._raise_readable_drive_error(exc)
            raise
        finally:
            if media is not None:
                try:
                    media.stream().close()
                except Exception:
                    pass

            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except PermissionError:
                    # Windows may keep the temp file locked briefly after Google API upload.
                    # Do not fail an otherwise successful upload because of temp cleanup.
                    pass


    async def upload_local_file(
        self,
        *,
        path: str | os.PathLike,
        object_key: str,
        content_type: str = "application/pdf",
    ) -> dict[str, Any]:
        """Upload a local file path to Google Drive and return StorageInfo fields.

        This is used by the AI-Extract integration after topic/lesson/chunk PDFs
        have already been produced in the local extraction workspace.
        """
        local_path = os.fspath(path)
        size = os.path.getsize(local_path)
        media = None
        try:
            object_parts = [part for part in object_key.strip("/").split("/") if part]
            if not object_parts:
                raise ValueError("object_key must not be empty")

            filename = object_parts[-1]
            folder_parts = object_parts[:-1]
            parent_folder_id = self.ensure_drive_path(folder_parts)

            media = MediaFileUpload(local_path, mimetype=content_type, resumable=True)
            metadata = {"name": filename, "parents": [parent_folder_id]}

            existing_file_id = self.find_file_in_folder(filename=filename, parent_id=parent_folder_id)
            if existing_file_id:
                created = (
                    self.client.files()
                    .update(
                        fileId=existing_file_id,
                        body={"name": filename},
                        media_body=media,
                        fields="id,name,mimeType,size,webViewLink,webContentLink,parents",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
            else:
                created = (
                    self.client.files()
                    .create(
                        body=metadata,
                        media_body=media,
                        fields="id,name,mimeType,size,webViewLink,webContentLink,parents",
                        supportsAllDrives=True,
                    )
                    .execute()
                )

            if settings.GOOGLE_DRIVE_MAKE_PUBLIC:
                self.make_file_public(created["id"])
                created = (
                    self.client.files()
                    .get(
                        fileId=created["id"],
                        fields="id,name,mimeType,size,webViewLink,webContentLink,parents",
                        supportsAllDrives=True,
                    )
                    .execute()
                )

            return {
                "provider": "google_drive",
                "objectKey": object_key,
                "rootFolderId": self.root_folder_id,
                "folderId": parent_folder_id,
                "fileId": created.get("id"),
                "webViewLink": created.get("webViewLink"),
                "webContentLink": created.get("webContentLink"),
                "mimeType": created.get("mimeType") or content_type,
                "sizeBytes": int(created.get("size") or size),
            }
        except HttpError as exc:
            self._raise_readable_drive_error(exc)
            raise
        finally:
            if media is not None:
                try:
                    media.stream().close()
                except Exception:
                    pass

    def get_file_url(self, storage: dict[str, Any]) -> str:
        """Return a view URL for a Google Drive stored file."""
        web_view_link = storage.get("webViewLink")
        if web_view_link:
            return web_view_link

        file_id = storage.get("fileId")
        if not file_id:
            raise ValueError("Document storage is missing Google Drive fileId")

        return f"https://drive.google.com/file/d/{file_id}/view"

    def download_file_to_memory(self, file_id: str) -> io.BytesIO:
        """Download a Google Drive binary file into memory for backend proxy download."""
        request = self.client.files().get_media(fileId=file_id, supportsAllDrives=True)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return buffer

    def ensure_drive_path(self, folder_parts: list[str]) -> str:
        """Create/reuse nested Google Drive folders below root and return final folder ID."""
        parent_id = self.root_folder_id
        for folder_name in folder_parts:
            parent_id = self.get_or_create_folder(folder_name=folder_name, parent_id=parent_id)
        return parent_id

    def find_file_in_folder(self, *, filename: str, parent_id: str) -> str | None:
        escaped_name = self._escape_drive_query_value(filename)
        query = (
            f"name = '{escaped_name}' "
            f"and '{parent_id}' in parents "
            f"and mimeType != '{GOOGLE_DRIVE_FOLDER_MIME_TYPE}' "
            "and trashed = false"
        )
        result = (
            self.client.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id,name)",
                pageSize=1,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        files = result.get("files", [])
        return files[0]["id"] if files else None

    def get_or_create_folder(self, *, folder_name: str, parent_id: str) -> str:
        escaped_name = self._escape_drive_query_value(folder_name)
        query = (
            f"name = '{escaped_name}' "
            f"and mimeType = '{GOOGLE_DRIVE_FOLDER_MIME_TYPE}' "
            f"and '{parent_id}' in parents "
            "and trashed = false"
        )

        result = (
            self.client.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id,name)",
                pageSize=1,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        files = result.get("files", [])
        if files:
            return files[0]["id"]

        created = (
            self.client.files()
            .create(
                body={
                    "name": folder_name,
                    "mimeType": GOOGLE_DRIVE_FOLDER_MIME_TYPE,
                    "parents": [parent_id],
                },
                fields="id,name",
                supportsAllDrives=True,
            )
            .execute()
        )
        return created["id"]

    def make_file_public(self, file_id: str) -> None:
        self.client.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
            supportsAllDrives=True,
        ).execute()

    @staticmethod
    def _escape_drive_query_value(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    @staticmethod
    def _raise_readable_drive_error(exc: HttpError) -> None:
        content = getattr(exc, "content", b"")
        if isinstance(content, bytes):
            content_text = content.decode("utf-8", errors="ignore")
        else:
            content_text = str(content)

        if "Service Accounts do not have storage quota" in content_text or "storageQuotaExceeded" in content_text:
            raise RuntimeError(
                "Google Drive upload failed because Service Accounts do not have personal storage quota. "
                "For local/personal Drive, set GOOGLE_DRIVE_AUTH_MODE=oauth and use an OAuth Desktop client. "
                "Only use GOOGLE_DRIVE_AUTH_MODE=service_account with a Shared Drive root folder."
            ) from exc

        raise RuntimeError(f"Google Drive upload failed: {exc}") from exc
