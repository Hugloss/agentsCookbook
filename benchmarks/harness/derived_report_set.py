"""Generation-bound publication for canonical derived benchmark reports."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .identity import canonical_json, digest


REPORT_SET_CONTRACT = "agents-cookbook-derived-report-set.v1"
REPORT_SET_MANIFEST = "report-set.json"
REPORT_SET_ARTIFACTS = (
    "report.json",
    "trace-diagnostics.json",
    "decision-evidence.json",
)


class DerivedReportSetError(ValueError):
    pass


def _reports_dir(run_root: Path) -> Path:
    return run_root / "reports"


def _encoded_json(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _artifact_receipt(payload: bytes) -> dict[str, Any]:
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def _manifest_payload(
    *,
    run_id: str,
    encoded: Mapping[str, bytes],
) -> dict[str, Any]:
    artifacts = {
        name: _artifact_receipt(encoded[name])
        for name in REPORT_SET_ARTIFACTS
    }
    identity = {
        "contract": REPORT_SET_CONTRACT,
        "run_id": run_id,
        "artifacts": artifacts,
    }
    return {
        **identity,
        "generation_id": digest(identity),
    }


def _fsync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_report_set(
    *,
    run_root: Path,
    run_id: str,
    report: object,
    trace_diagnostics: object,
    decision_evidence: object,
) -> dict[str, Any]:
    """Publish one canonical report generation with the manifest last.

    Individual artifact replacement is not a multi-file transaction. Publishing
    the checksum-bound manifest last makes every intermediate/torn state
    detectable and therefore non-authoritative.
    """
    directory = _reports_dir(run_root)
    directory.mkdir(parents=True, exist_ok=True)
    if directory.is_symlink() or not directory.is_dir():
        raise DerivedReportSetError("reports directory is not a regular directory")

    payloads = {
        "report.json": report,
        "trace-diagnostics.json": trace_diagnostics,
        "decision-evidence.json": decision_evidence,
    }
    encoded = {
        name: _encoded_json(payloads[name])
        for name in REPORT_SET_ARTIFACTS
    }
    manifest = _manifest_payload(run_id=run_id, encoded=encoded)
    manifest_bytes = canonical_json(manifest)

    staged = Path(
        tempfile.mkdtemp(
            prefix=".report-set-stage-",
            dir=directory,
        )
    )
    try:
        for name in REPORT_SET_ARTIFACTS:
            destination = staged / name
            with destination.open("wb") as stream:
                stream.write(encoded[name])
                stream.flush()
                os.fsync(stream.fileno())

        staged_manifest = staged / REPORT_SET_MANIFEST
        with staged_manifest.open("wb") as stream:
            stream.write(manifest_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(staged)

        for name in REPORT_SET_ARTIFACTS:
            os.replace(staged / name, directory / name)
        _fsync_directory(directory)

        # The manifest is the commit record for the generation and must be last.
        os.replace(staged_manifest, directory / REPORT_SET_MANIFEST)
        _fsync_directory(directory)
    finally:
        shutil.rmtree(staged, ignore_errors=True)

    return verify_report_set(run_root=run_root, expected_run_id=run_id)


def inspect_report_set(
    *,
    run_root: Path,
    expected_run_id: str | None = None,
) -> dict[str, Any]:
    """Project report-set health without treating legacy unbound files as verified."""
    directory = _reports_dir(run_root)
    manifest_path = directory / REPORT_SET_MANIFEST
    if not manifest_path.exists():
        present = [
            name
            for name in REPORT_SET_ARTIFACTS
            if (directory / name).is_file()
        ]
        return {
            "status": "UNBOUND" if present else "NOT_PUBLISHED",
            "verified": False,
            "artifacts_present": present,
        }
    try:
        manifest = verify_report_set(
            run_root=run_root,
            expected_run_id=expected_run_id,
        )
    except DerivedReportSetError as exc:
        return {
            "status": "INVALID",
            "verified": False,
            "reason": str(exc),
        }
    return {
        "status": "VERIFIED",
        "verified": True,
        "generation_id": manifest["generation_id"],
        "run_id": manifest["run_id"],
        "artifacts": sorted(manifest["artifacts"]),
    }


def verify_report_set(
    *,
    run_root: Path,
    expected_run_id: str | None = None,
) -> dict[str, Any]:
    """Verify the canonical derived report generation from exact persisted bytes."""
    directory = _reports_dir(run_root)
    manifest_path = directory / REPORT_SET_MANIFEST
    if not manifest_path.exists():
        raise DerivedReportSetError("canonical derived report set has no manifest")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise DerivedReportSetError("derived report-set manifest is not a regular file")

    try:
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise DerivedReportSetError("cannot read derived report-set manifest") from exc

    required = {"contract", "run_id", "artifacts", "generation_id"}
    if (
        not isinstance(manifest, dict)
        or set(manifest) != required
        or canonical_json(manifest) != raw
        or manifest.get("contract") != REPORT_SET_CONTRACT
        or not isinstance(manifest.get("run_id"), str)
        or not manifest["run_id"]
        or not isinstance(manifest.get("artifacts"), dict)
        or set(manifest["artifacts"]) != set(REPORT_SET_ARTIFACTS)
        or not isinstance(manifest.get("generation_id"), str)
    ):
        raise DerivedReportSetError("derived report-set manifest identity mismatch")

    if expected_run_id is not None and manifest["run_id"] != expected_run_id:
        raise DerivedReportSetError(
            "derived report-set run identity mismatch "
            f"(expected {expected_run_id}, observed {manifest['run_id']})"
        )

    identity = {
        "contract": manifest["contract"],
        "run_id": manifest["run_id"],
        "artifacts": manifest["artifacts"],
    }
    if manifest["generation_id"] != digest(identity):
        raise DerivedReportSetError("derived report-set generation digest mismatch")

    for name in REPORT_SET_ARTIFACTS:
        receipt = manifest["artifacts"].get(name)
        if (
            not isinstance(receipt, dict)
            or set(receipt) != {"sha256", "bytes"}
            or not isinstance(receipt.get("sha256"), str)
            or type(receipt.get("bytes")) is not int
            or receipt["bytes"] < 0
        ):
            raise DerivedReportSetError(
                f"invalid derived report-set artifact receipt: {name}"
            )
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise DerivedReportSetError(
                f"derived report-set artifact is missing or non-regular: {name}"
            )
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise DerivedReportSetError(
                f"cannot read derived report-set artifact: {name}"
            ) from exc
        if (
            len(payload) != receipt["bytes"]
            or hashlib.sha256(payload).hexdigest() != receipt["sha256"]
        ):
            raise DerivedReportSetError(
                f"derived report-set artifact does not match manifest: {name}"
            )
        try:
            json.loads(payload)
        except ValueError as exc:
            raise DerivedReportSetError(
                f"derived report-set artifact is not JSON: {name}"
            ) from exc

    return manifest
