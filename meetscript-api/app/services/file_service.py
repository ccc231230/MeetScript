"""Unified file storage abstraction with MinIO/OSS/S3 backends."""

import hashlib
import io
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    async def upload(self, file_data: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
        """Upload file bytes, return object URL."""
        ...

    @abstractmethod
    async def get_presigned_upload_url(self, object_key: str, expires: int = 3600) -> str:
        """Generate a presigned URL for direct upload."""
        ...

    @abstractmethod
    async def get_presigned_download_url(self, object_key: str, expires: int = 3600) -> str:
        """Generate a presigned URL for download."""
        ...

    @abstractmethod
    async def download(self, object_key: str) -> bytes:
        """Download file bytes."""
        ...

    @abstractmethod
    async def stream(self, object_key: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
        """Stream file chunks (for large file / media serving)."""
        ...

    @abstractmethod
    async def get_size(self, object_key: str) -> Optional[int]:
        """Get file size in bytes, or None if not found."""
        ...

    @abstractmethod
    async def delete(self, object_key: str) -> None:
        """Delete an object."""
        ...

    @abstractmethod
    async def initiate_multipart_upload(self, object_key: str, content_type: str = "application/octet-stream") -> str:
        """Initiate multipart upload, return upload_id."""
        ...

    @abstractmethod
    async def get_presigned_part_url(self, object_key: str, upload_id: str, part_number: int, expires: int = 3600) -> str:
        """Generate presigned URL for a single part."""
        ...

    @abstractmethod
    async def complete_multipart_upload(self, object_key: str, upload_id: str, parts: list[dict]) -> str:
        """Complete multipart upload, return object URL."""
        ...

    @abstractmethod
    async def abort_multipart_upload(self, object_key: str, upload_id: str) -> None:
        """Abort a multipart upload."""
        ...


class MinIOBackend(StorageBackend):
    """MinIO storage backend implementation."""

    def __init__(self):
        from minio import Minio

        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY.get_secret_value(),
            secret_key=settings.MINIO_SECRET_KEY.get_secret_value(),
            secure=settings.MINIO_SECURE,
        )
        self._bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        import asyncio

        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    async def upload(self, file_data: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.put_object(
                self._bucket, object_key, io.BytesIO(file_data), len(file_data), content_type=content_type
            ),
        )
        return f"minio://{self._bucket}/{object_key}"

    async def get_presigned_upload_url(self, object_key: str, expires: int = 3600) -> str:
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._client.presigned_put_object(
                self._bucket, object_key, expires=timedelta(seconds=expires)
            ),
        )

    async def get_presigned_download_url(self, object_key: str, expires: int = 3600) -> str:
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._client.presigned_get_object(
                self._bucket, object_key, expires=timedelta(seconds=expires)
            ),
        )

    async def download(self, object_key: str) -> bytes:
        import asyncio

        loop = asyncio.get_event_loop()

        def _download():
            resp = self._client.get_object(self._bucket, object_key)
            return resp.read()

        return await loop.run_in_executor(None, _download)

    async def stream(self, object_key: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
        import asyncio

        loop = asyncio.get_event_loop()

        def _get_stream():
            return self._client.get_object(self._bucket, object_key)

        response = await loop.run_in_executor(None, _get_stream)
        try:
            while True:
                chunk = await loop.run_in_executor(None, response.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            response.close()
            response.release_conn()

    async def get_size(self, object_key: str) -> Optional[int]:
        import asyncio

        loop = asyncio.get_event_loop()
        try:
            stat = await loop.run_in_executor(
                None, lambda: self._client.stat_object(self._bucket, object_key)
            )
            return stat.size
        except Exception:
            return None

    async def delete(self, object_key: str) -> None:
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._client.remove_object(self._bucket, object_key))

    async def initiate_multipart_upload(self, object_key: str, content_type: str = "application/octet-stream") -> str:
        # MinIO SDK does not have explicit multipart initiation for presigned approach
        # Use a simple upload ID based on object key
        return hashlib.md5(f"{object_key}:{uuid.uuid4()}".encode()).hexdigest()

    async def get_presigned_part_url(self, object_key: str, upload_id: str, part_number: int, expires: int = 3600) -> str:
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._client.presigned_put_object(
                self._bucket,
                f"{object_key}.part{part_number}",
                expires=timedelta(seconds=expires),
            ),
        )

    async def complete_multipart_upload(self, object_key: str, upload_id: str, parts: list[dict]) -> str:
        import asyncio

        loop = asyncio.get_event_loop()

        def _compose():
            sources = [f"{object_key}.part{p['PartNumber']}" for p in sorted(parts, key=lambda x: x["PartNumber"])]
            # MinIO compose objects
            from minio.commonconfig import ComposeSource

            compose_sources = [ComposeSource(self._bucket, src) for src in sources]
            result = self._client.compose_object(self._bucket, object_key, compose_sources)
            # Clean up parts
            for src in sources:
                try:
                    self._client.remove_object(self._bucket, src)
                except Exception:
                    pass
            return result

        await loop.run_in_executor(None, _compose)
        return f"minio://{self._bucket}/{object_key}"

    async def abort_multipart_upload(self, object_key: str, upload_id: str) -> None:
        # Cleanup any partial uploads
        import asyncio

        loop = asyncio.get_event_loop()

        def _cleanup():
            objects = self._client.list_objects(self._bucket, prefix=f"{object_key}.part")
            for obj in objects:
                try:
                    self._client.remove_object(self._bucket, obj.object_name)
                except Exception:
                    pass

        await loop.run_in_executor(None, _cleanup)


class OSSBackend(StorageBackend):
    """Aliyun OSS storage backend (placeholder - requires oss2 SDK)."""

    def __init__(self):
        import oss2

        self._auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID.get_secret_value() if settings.OSS_ACCESS_KEY_ID else "",
            settings.OSS_ACCESS_KEY_SECRET.get_secret_value() if settings.OSS_ACCESS_KEY_SECRET else "",
        )
        self._bucket_obj = oss2.Bucket(self._auth, settings.OSS_ENDPOINT or "", settings.OSS_BUCKET or "")
        self._bucket = settings.OSS_BUCKET or ""

    async def upload(self, file_data: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._bucket_obj.put_object(object_key, file_data))
        return f"oss://{self._bucket}/{object_key}"

    async def get_presigned_upload_url(self, object_key: str, expires: int = 3600) -> str:
        return self._bucket_obj.sign_url("PUT", object_key, expires)

    async def get_presigned_download_url(self, object_key: str, expires: int = 3600) -> str:
        return self._bucket_obj.sign_url("GET", object_key, expires)

    async def download(self, object_key: str) -> bytes:
        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: self._bucket_obj.get_object(object_key))
        return result.read()

    async def stream(self, object_key: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
        """Stream file chunks from OSS (not yet implemented for OSS)."""
        import asyncio

        data = await self.download(object_key)
        # Fallback: yield entire content as one chunk.
        yield data

    async def get_size(self, object_key: str) -> Optional[int]:
        import asyncio

        loop = asyncio.get_event_loop()
        try:
            meta = await loop.run_in_executor(
                None, lambda: self._bucket_obj.head_object(object_key)
            )
            return meta.content_length
        except Exception:
            return None

    async def delete(self, object_key: str) -> None:
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._bucket_obj.delete_object(object_key))

    async def initiate_multipart_upload(self, object_key: str, content_type: str = "application/octet-stream") -> str:
        import asyncio
        import oss2

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._bucket_obj.init_multipart_upload(object_key),
        )
        return result.upload_id

    async def get_presigned_part_url(self, object_key: str, upload_id: str, part_number: int, expires: int = 3600) -> str:
        return self._bucket_obj.sign_url(
            "PUT", object_key, expires, params={"uploadId": upload_id, "partNumber": str(part_number)}
        )

    async def complete_multipart_upload(self, object_key: str, upload_id: str, parts: list[dict]) -> str:
        import asyncio
        import oss2
        from oss2.models import PartInfo

        loop = asyncio.get_event_loop()
        part_info_list = [PartInfo(p["PartNumber"], p["ETag"]) for p in parts]
        await loop.run_in_executor(
            None,
            lambda: self._bucket_obj.complete_multipart_upload(object_key, upload_id, part_info_list),
        )
        return f"oss://{self._bucket}/{object_key}"

    async def abort_multipart_upload(self, object_key: str, upload_id: str) -> None:
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._bucket_obj.abort_multipart_upload(object_key, upload_id),
        )


# ── Factory ────────────────────────────────────────────────────────

_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Factory: return the configured storage backend singleton."""
    global _storage_instance
    if _storage_instance is None:
        backend = settings.STORAGE_BACKEND
        if backend == "oss":
            _storage_instance = OSSBackend()
        else:
            _storage_instance = MinIOBackend()
    return _storage_instance


class FileService:
    """High-level file management service."""

    CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB per part for multipart upload
    CHUNK_THRESHOLD = 10 * 1024 * 1024  # Use multipart for files > 10 MB

    def __init__(self):
        self._storage = get_storage()

    def _generate_object_key(self, user_id: str, filename: str) -> str:
        """Generate a unique object key for storage."""
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        uid = uuid.uuid4().hex[:12]
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename.rsplit(".", 1)[0])[:64]
        return f"meetings/{user_id}/{safe_name}_{uid}.{ext}"

    async def get_upload_url(self, user_id: str, filename: str, content_type: Optional[str] = None) -> dict:
        """Generate a presigned upload URL."""
        object_key = self._generate_object_key(user_id, filename)
        url = await self._storage.get_presigned_upload_url(object_key)
        # Rewrite internal MinIO URL to browser-accessible proxy path.
        # Vite proxies /storage/ -> minio:9000/ with changeOrigin (Host=minio:9000),
        # so the presigned signature remains valid.
        url = url.replace(f"http://{settings.MINIO_ENDPOINT}", "/storage")
        return {"upload_url": url, "object_key": object_key, "expires_in": 3600}

    async def get_download_url(self, object_key: str, expires: int = 3600) -> str:
        """Generate a presigned download URL (browser-accessible via /storage proxy)."""
        url = await self._storage.get_presigned_download_url(object_key, expires)
        url = url.replace(f"http://{settings.MINIO_ENDPOINT}", "/storage")
        return url

    async def get_raw_download_url(self, object_key: str, expires: int = 3600) -> str:
        """Generate a raw presigned download URL (for internal/external services like ASR).

        Uses PUBLIC_STORAGE_BASE_URL if configured (e.g. ngrok tunnel for dev),
        otherwise returns the raw MinIO endpoint URL (Docker-internal only).
        """
        raw_url = await self._storage.get_presigned_download_url(object_key, expires)
        base = getattr(settings, "PUBLIC_STORAGE_BASE_URL", None)
        if base and base.strip():
            # Replace the internal MinIO host with the public base URL
            raw_url = raw_url.replace(
                f"http://{settings.MINIO_ENDPOINT}", base.rstrip("/")
            )
        return raw_url

    async def upload_file(self, user_id: str, file_data: bytes, filename: str, content_type: str = "application/octet-stream") -> dict:
        """Directly upload a file through the backend."""
        object_key = self._generate_object_key(user_id, filename)
        url = await self._storage.upload(file_data, object_key, content_type)
        return {"object_key": object_key, "url": url}

    async def upload_file_stream(self, user_id: str, file_obj, filename: str, content_type: str = "application/octet-stream", file_size: int = -1) -> dict:
        """Upload a file using a stream (avoids loading the entire file into memory).

        Args:
            user_id: User ID for object key generation.
            file_obj: A file-like object with read() method (e.g., SpooledTemporaryFile).
            filename: Original filename.
            content_type: MIME type.
            file_size: Known file size in bytes (-1 if unknown).
        """
        import asyncio

        object_key = self._generate_object_key(user_id, filename)
        storage = self._storage

        if isinstance(storage, MinIOBackend):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: storage._client.put_object(
                    storage._bucket, object_key, file_obj, file_size, content_type=content_type,
                ),
            )
            url = f"minio://{storage._bucket}/{object_key}"
        else:
            # Fallback: read entire stream into memory for non-MinIO backends
            content = file_obj.read()
            if isinstance(content, str):
                content = content.encode()
            url = await storage.upload(content, object_key, content_type)

        return {"object_key": object_key, "url": url}

    async def download_file(self, object_key: str) -> bytes:
        """Download a file from storage (returns raw bytes)."""
        return await self._storage.download(object_key)

    async def delete_file(self, object_key: str) -> None:
        """Delete a file from storage."""
        await self._storage.delete(object_key)

    async def stream_file(self, object_key: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
        """Stream file from storage in chunks (for media serving)."""
        async for chunk in self._storage.stream(object_key, chunk_size):
            yield chunk

    async def get_file_size(self, object_key: str) -> Optional[int]:
        """Get file size from storage."""
        return await self._storage.get_size(object_key)

    async def initiate_multipart(self, user_id: str, filename: str, content_type: str = "application/octet-stream") -> dict:
        """Initiate a multipart upload."""
        object_key = self._generate_object_key(user_id, filename)
        upload_id = await self._storage.initiate_multipart_upload(object_key, content_type)
        return {"object_key": object_key, "upload_id": upload_id}

    async def get_part_upload_url(self, object_key: str, upload_id: str, part_number: int) -> str:
        """Get a presigned URL for uploading a single part."""
        return await self._storage.get_presigned_part_url(object_key, upload_id, part_number)

    async def complete_multipart(self, object_key: str, upload_id: str, parts: list[dict]) -> str:
        """Complete a multipart upload."""
        return await self._storage.complete_multipart_upload(object_key, upload_id, parts)

    def uses_multipart(self, file_size_bytes: int) -> bool:
        """Determine whether to use multipart upload."""
        return file_size_bytes > self.CHUNK_THRESHOLD


# Singleton
file_service = FileService()
