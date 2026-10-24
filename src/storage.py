"""Storage provider supporting both local storage and S3/MinIO."""
import abc
import os
import uuid
from pathlib import Path
from typing import Tuple, Union
import httpx

from src.config import settings
from src.logger import logger


class StorageProvider(abc.ABC):
    @abc.abstractmethod
    def save(self, filename: str, content: Union[bytes, str], content_type: str = "application/json") -> Tuple[str, str]:
        """Saves content and returns (storage_key, download_url)."""
        pass

    @abc.abstractmethod
    def get(self, storage_key: str) -> bytes:
        """Retrieves content by storage_key."""
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: Union[bytes, str], content_type: str = "application/json") -> Tuple[str, str]:
        unique_id = uuid.uuid4().hex[:8]
        safe_name = f"{unique_id}_{Path(filename).name}"
        file_path = self.base_dir / safe_name
        data = content.encode("utf-8") if isinstance(content, str) else content
        with open(file_path, "wb") as f:
            f.write(data)
        
        # Download URL relative to service API
        download_url = f"/api/v1/storage/{safe_name}"
        return safe_name, download_url

    def get(self, storage_key: str) -> bytes:
        safe_path = self.base_dir / Path(storage_key).name
        if not safe_path.exists():
            raise FileNotFoundError(f"Storage key {storage_key} not found")
        with open(safe_path, "rb") as f:
            return f.read()


class S3StorageProvider(StorageProvider):
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str, region: str):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region = region
        self._s3_client = None

    def _get_client(self):
        if self._s3_client is None:
            try:
                import boto3
                self._s3_client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                )
                try:
                    self._s3_client.create_bucket(Bucket=self.bucket_name)
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"S3 client init failed, fallback: {e}")
                self._s3_client = None
        return self._s3_client

    def save(self, filename: str, content: Union[bytes, str], content_type: str = "application/json") -> Tuple[str, str]:
        client = self._get_client()
        unique_id = uuid.uuid4().hex[:8]
        key = f"{unique_id}_{Path(filename).name}"
        data = content.encode("utf-8") if isinstance(content, str) else content
        if client:
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            download_url = f"{self.endpoint_url}/{self.bucket_name}/{key}"
            return key, download_url
        else:
            # Fallback to local storage if S3 service is unavailable
            fallback = LocalStorageProvider(settings.STORAGE_LOCAL_DIR)
            return fallback.save(filename, content, content_type)

    def get(self, storage_key: str) -> bytes:
        client = self._get_client()
        if client:
            response = client.get_object(Bucket=self.bucket_name, Key=storage_key)
            return response["Body"].read()
        fallback = LocalStorageProvider(settings.STORAGE_LOCAL_DIR)
        return fallback.get(storage_key)


def get_storage() -> StorageProvider:
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageProvider(
            endpoint_url=settings.S3_ENDPOINT_URL,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            bucket_name=settings.S3_BUCKET_NAME,
            region=settings.S3_REGION,
        )
    return LocalStorageProvider(settings.STORAGE_LOCAL_DIR)


async def fetch_or_read_input(input_source: str) -> str:
    """Accepts inputs as raw text, file path, or URL (Integration Standard point 7)."""
    if input_source.startswith("http://") or input_source.startswith("https://"):
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(input_source)
            resp.raise_for_status()
            return resp.text
    elif os.path.exists(input_source):
        with open(input_source, "r", encoding="utf-8") as f:
            return f.read()
    return input_source
