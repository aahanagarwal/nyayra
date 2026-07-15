"""Local filesystem storage for uploaded and generated files.

Files live flat under settings.storage_path, named by a generated id (which
doubles as the path). Twilio and the frontend fetch them back over HTTP via
GET /api/files/{id} (see app/api/documents.py), so ids must be safe to drop
straight into a URL and must never escape the storage directory.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import get_settings


def _storage_dir() -> Path:
    directory = Path(get_settings().storage_path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _resolve(file_id: str) -> Path:
    """Map a file id back to its on-disk path, rejecting traversal attempts."""
    name = Path(file_id).name
    if not name or name != file_id:
        raise ValueError(f"invalid file id: {file_id!r}")
    return _storage_dir() / name


def save_bytes(data: bytes, name: str) -> str:
    """Write bytes under storage_path with a fresh unique name; returns that name (the file id)."""
    suffix = Path(name).suffix
    file_id = f"{uuid.uuid4().hex}{suffix}"
    (_storage_dir() / file_id).write_bytes(data)
    return file_id


def read_bytes(file_id: str) -> bytes:
    return _resolve(file_id).read_bytes()


def full_path(file_id: str) -> Path:
    """Absolute on-disk path for a stored file id, for handing to FileResponse."""
    return _resolve(file_id)


def public_url(file_id: str) -> str:
    return f"{get_settings().public_base_url}/api/files/{Path(file_id).name}"
