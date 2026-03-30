"""MinIO document storage helpers."""

import io
import os

from minio import Minio
from minio.error import S3Error

BUCKET = 'kanapi'

_client = Minio(
    os.environ.get('MINIO_ENDPOINT', 'localhost:9000'),
    access_key=os.environ.get('MINIO_ACCESS_KEY', 'minioadmin'),
    secret_key=os.environ.get('MINIO_SECRET_KEY', 'minioadmin'),
    secure=os.environ.get('MINIO_SECURE', 'false').lower() in ('true', '1', 'yes'),
)


def _sanitize_filename(filename: str) -> str:
    """Validate and sanitize a filename to prevent path traversal."""
    if not filename or '\0' in filename:
        raise ValueError('Invalid filename')
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValueError('Invalid filename: path traversal detected')
    return filename


def ensure_bucket() -> None:
    """Create the kanapi bucket if it does not already exist."""
    if not _client.bucket_exists(BUCKET):
        _client.make_bucket(BUCKET)


def list_case_documents(case_id: str) -> list[dict]:
    """Return metadata for non-markdown objects under cases/{case_id}/, with has_markdown flag."""
    try:
        objs = list(_client.list_objects(BUCKET, prefix=f'cases/{case_id}/', recursive=True))
        names = {o.object_name.split('/')[-1] for o in objs if not o.object_name.endswith('/')}
        return [
            {
                'name': o.object_name.split('/')[-1],
                'size': o.size,
                'last_modified': o.last_modified,
                'has_markdown': (o.object_name.split('/')[-1].rsplit('.', 1)[0] + '.md') in names,
            }
            for o in objs
            if not o.object_name.endswith('/') and not o.object_name.endswith('.md')
        ]
    except S3Error:
        return []


def delete_case_documents(case_id: str) -> None:
    """Delete all objects stored under cases/{case_id}/."""
    try:
        objs = _client.list_objects(BUCKET, prefix=f'cases/{case_id}/', recursive=True)
        for o in objs:
            _client.remove_object(BUCKET, o.object_name)
    except S3Error:
        pass


def delete_case_document(case_id: str, filename: str) -> None:
    """Delete a single document from MinIO."""
    safe_name = _sanitize_filename(filename)
    _client.remove_object(BUCKET, f'cases/{case_id}/{safe_name}')


def upload_case_document(case_id: str, filename: str, data: bytes, content_type: str) -> str:
    """Upload bytes to MinIO at cases/{case_id}/{filename}. Returns the object key."""
    safe_name = _sanitize_filename(filename)
    object_key = f'cases/{case_id}/{safe_name}'
    _client.put_object(BUCKET, object_key, io.BytesIO(data), length=len(data), content_type=content_type)
    return object_key


def stream_case_document(case_id: str, filename: str) -> tuple:
    """Return (HTTPResponse, content_type) for the requested document."""
    safe_name = _sanitize_filename(filename)
    obj = _client.get_object(BUCKET, f'cases/{case_id}/{safe_name}')
    content_type = obj.headers.get('content-type', 'application/octet-stream')
    return obj, content_type
