import io
import logging
from uuid import UUID, uuid4

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 25_000_000   # protege contra decompression bombs

logger = logging.getLogger(__name__)


class InvalidImageError(Exception):
    """El archivo subido no es una imagen válida."""


class PhotoNotFoundError(Exception):
    """La foto no existe en uploads/."""


class PhotoTooLargeError(Exception):
    """La foto supera el tamaño máximo permitido."""


class S3Process:
    MAX_SIZE = 5 * 1024 * 1024
    MAX_DIM = 800

    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.s3 = boto3.client(
            "s3",
            region_name=region,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},   
            ),
        )


    
    @staticmethod
    def _upload_key(account_uuid: str, photo_id: UUID | str) -> str:
        return f"tmp/drivers/{account_uuid}/{photo_id}"

    @staticmethod
    def _driver_key(account_uuid: str, photo_id: UUID | str) -> str:
        return f"drivers/{account_uuid}/{photo_id}.webp"


    async def store_upload(self, account_uuid: str, data: bytes) -> str:
        if len(data) > self.MAX_SIZE:
            raise PhotoTooLargeError()
        photo_id = uuid4()
        await run_in_threadpool(
            self.s3.put_object,
            Bucket=self.bucket,
            Key=self._upload_key(account_uuid, photo_id),
            Body=data,
        )
        return str(photo_id)

    async def finalize_photo(self, account_uuid: str, photo_id: UUID) -> str:

        return await run_in_threadpool(self._finalize_photo, account_uuid, photo_id)

    async def delete_photo(self, key: str) -> None:
        await run_in_threadpool(self.s3.delete_object, Bucket=self.bucket, Key=key)

    def get_photo_url(self, key: str | None, expires: int = 3600) -> str | None:
        if not key:
            return None
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )


    def _finalize_photo(self, account_uuid: str, photo_id: UUID) -> str:
        src = self._upload_key(account_uuid, photo_id)
        dst = self._driver_key(account_uuid, photo_id)

        try:
            data = self.s3.get_object(Bucket=self.bucket, Key=src)["Body"].read()
        except ClientError as e:
            raise PhotoNotFoundError(src) from e

        processed = self._process_image(data)

        self.s3.put_object(
            Bucket=self.bucket,
            Key=dst,
            Body=processed,
            ContentType="image/webp",
        )
        self.s3.delete_object(Bucket=self.bucket, Key=src)
        return dst

    @classmethod
    def _process_image(cls, data: bytes) -> bytes:
        try:
            Image.open(io.BytesIO(data)).verify()                 
            img = Image.open(io.BytesIO(data)).convert("RGB")    
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
            logger.warning("Imagen inválida: %s", e)
            raise InvalidImageError() from e

        img.thumbnail((cls.MAX_DIM, cls.MAX_DIM))
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=85)
        return out.getvalue()


    @staticmethod
    def _owns_key(account_uuid: str, key: str) -> bool:
        return key.startswith(f"drivers/{account_uuid}/")

    async def safe_delete(self, account_uuid: str, key: str | None) -> None:
        if not key:
            return
        if not self._owns_key(account_uuid, key):
            return
        try:
            await self.delete_photo(key)
        except Exception as err:
            print("Error deleting photo: ",err)