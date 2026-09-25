"""Crash-safe create-once trial receipt finalization."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .identity import canonical_json


class ReceiptExistsError(RuntimeError):
    pass


def _fsync_directory(directory: Path) -> None:
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_temp(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def is_complete_receipt(directory: Path) -> bool:
    result = directory / "result.json"
    checksum = directory / "result.sha256"
    completion = directory / "completion.json"
    if not all(path.is_file() for path in (result, checksum, completion)):
        return False
    try:
        payload = result.read_bytes()
        parsed = json.loads(payload)
        if canonical_json(parsed) != payload:
            return False
        actual = hashlib.sha256(payload).hexdigest()
        recorded = checksum.read_text(encoding="utf-8").strip().split()[0]
        complete = json.loads(completion.read_text(encoding="utf-8"))
    except (OSError, ValueError, IndexError, json.JSONDecodeError):
        return False
    return recorded == actual and complete == {"result_sha256": actual}


def write_receipt(directory: Path, receipt: dict[str, Any]) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    result = directory / "result.json"
    checksum = directory / "result.sha256"
    completion = directory / "completion.json"
    final_paths = (result, checksum, completion)
    if any(path.exists() for path in final_paths):
        raise ReceiptExistsError(f"trial receipt state already exists: {directory}")

    payload = canonical_json(receipt)
    receipt_sha = hashlib.sha256(payload).hexdigest()
    temporary = [
        directory / ".result.json.tmp",
        directory / ".result.sha256.tmp",
        directory / ".completion.json.tmp",
    ]
    if any(path.exists() for path in temporary):
        raise ReceiptExistsError(f"stale trial receipt temporary state exists: {directory}")

    try:
        _write_temp(temporary[0], payload)
        _write_temp(temporary[1], f"{receipt_sha}  result.json\n".encode())
        _write_temp(
            temporary[2],
            canonical_json({"result_sha256": receipt_sha}),
        )
        os.replace(temporary[0], result)
        os.replace(temporary[1], checksum)
        os.replace(temporary[2], completion)
        _fsync_directory(directory)
    except BaseException:
        for path in temporary:
            path.unlink(missing_ok=True)
        raise

    if not is_complete_receipt(directory):
        raise RuntimeError(f"receipt finalization verification failed: {directory}")
    return result, receipt_sha
