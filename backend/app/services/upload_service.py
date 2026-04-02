import uuid
import asyncio
import time
from functools import partial
from app.s3.service import s3
from app.config import Config

# Server-side presigned URL cache.
# S3 presigned URLs contain the signing timestamp, so they change on every call.
# Without caching, each API poll returns different URLs → browsers re-download
# every image every 15s instead of serving from cache.
# We cache for 50 min (S3 URLs are valid for 1 hour).
_presigned_cache: dict[str, tuple[str, float]] = {}
_PRESIGN_TTL = 50 * 60  # 50 minutes in seconds


def _sync_put_object(key: str, body: bytes, content_type: str) -> None:
    s3.put_object(
        Bucket=Config.AWS_BUCKET,
        Key=key,
        Body=body,
        ContentType=content_type
    )


async def upload_file_to_s3(file):
    try:
        contents = await file.read()
        extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        key = f"uploads/{uuid.uuid4()}.{extension}"

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(_sync_put_object, key, contents, file.content_type or "image/jpeg")
        )

        file_url = f"https://{Config.AWS_BUCKET}.s3.{Config.AWS_REGION}.amazonaws.com/{key}"
        return {"file_name": file.filename, "file_url": file_url, "key": key}
    except Exception as e:
        print(f"Error uploading {file.filename} to S3: {e}")
        return None


def generate_presigned_url_from_key(key: str, expires_in: int = 3600) -> str:
    """Return a stable presigned GET URL directly from an S3 object key.
    Preferred over generate_presigned_get_url when s3_key is stored on the Photo row,
    because it doesn't depend on URL format remaining stable."""
    try:
        cached = _presigned_cache.get(key)
        if cached and time.monotonic() < cached[1]:
            return cached[0]
        signed = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": Config.AWS_BUCKET, "Key": key},
            ExpiresIn=expires_in
        )
        _presigned_cache[key] = (signed, time.monotonic() + _PRESIGN_TTL)
        return signed
    except Exception:
        return f"https://{Config.AWS_BUCKET}.s3.{Config.AWS_REGION}.amazonaws.com/{key}"


def generate_presigned_get_url(url: str, expires_in: int = 3600) -> str:
    """Return a stable presigned GET URL for a stored S3 object.
    Kept for backward compatibility with photos that have no s3_key yet.
    Prefer generate_presigned_url_from_key when s3_key is available."""
    try:
        prefix = f"https://{Config.AWS_BUCKET}.s3.{Config.AWS_REGION}.amazonaws.com/"
        key = url[len(prefix):]
        return generate_presigned_url_from_key(key, expires_in)
    except Exception:
        return url
