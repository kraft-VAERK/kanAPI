"""MinIO document storage helpers."""

from minio import Minio
from minio.error import S3Error

BUCKET = 'kanapi'

_client = Minio(
    'localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False,
)


def ensure_bucket() -> None:
    """Create the kanapi bucket if it does not already exist."""
    if not _client.bucket_exists(BUCKET):
        _client.make_bucket(BUCKET)


def list_case_documents(case_id: str) -> list[dict]:
    """Return metadata for all objects stored under cases/{case_id}/."""
    try:
        objs = _client.list_objects(BUCKET, prefix=f'cases/{case_id}/', recursive=True)
        return [
            {
                'name': o.object_name.split('/')[-1],
                'size': o.size,
                'last_modified': o.last_modified,
            }
            for o in objs
            if not o.object_name.endswith('/')
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


def stream_case_document(case_id: str, filename: str) -> tuple:
    """Return (HTTPResponse, content_type) for the requested document."""
    obj = _client.get_object(BUCKET, f'cases/{case_id}/{filename}')
    content_type = obj.headers.get('content-type', 'application/octet-stream')
    return obj, content_type
