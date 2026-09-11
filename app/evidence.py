import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc)


def evidence_id():
    return str(uuid.uuid4())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_file(path: Path):
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def write_json_atomic(path: Path, payload: dict):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def build_manifest(config, camera, video_path: Path, started_at, ended_at=None):
    ended_at = ended_at or utc_now()
    stat = video_path.stat()
    return {
        "schema": "ai-legal.evidence.video.v1",
        "evidence_id": evidence_id(),
        "service": config.service_id,
        "service_version": config.service_version,
        "node_id": config.node_id,
        "capture": {
            "start_utc": started_at.isoformat().replace("+00:00", "Z"),
            "end_utc": ended_at.isoformat().replace("+00:00", "Z"),
            "start_monotonic_ns": time.monotonic_ns(),
            "clock_source": "system",
            "time_quality": "unsynchronized",
            "gps_authority": False,
        },
        "camera": camera,
        "video": {
            "filename": video_path.name,
            "bytes": stat.st_size,
            "sha256": sha256_file(video_path),
            "format": "h264",
            "codec": "h264",
            "width": config.width,
            "height": config.height,
            "framerate": config.framerate,
            "bitrate": config.bitrate,
        },
        "integrity": {
            "hash_algorithm": "SHA-256",
            "payload_immutable": True,
            "manifest_immutable": True,
        },
        "gps": None,
        "notes": [
            "Video is stored as segmented H.264 elementary streams in this release.",
            "Wall-clock time is not GPS disciplined in this release.",
        ],
    }
