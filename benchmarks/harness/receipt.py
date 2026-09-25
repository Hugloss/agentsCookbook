"""Create-once trial receipt writer."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from .identity import canonical_json, digest

class ReceiptExistsError(RuntimeError): pass

def write_receipt(directory: Path, receipt: dict[str, Any]) -> tuple[Path,str]:
    directory.mkdir(parents=True, exist_ok=True)
    target=directory/"result.json"; checksum=directory/"result.sha256"
    if target.exists() or checksum.exists(): raise ReceiptExistsError(f"trial receipt already exists: {directory}")
    payload=canonical_json(receipt); receipt_sha=digest(receipt)
    fd=os.open(target, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    except BaseException:
        target.unlink(missing_ok=True); raise
    checksum.write_text(f"{receipt_sha}  result.json\n",encoding="utf-8")
    return target,receipt_sha
