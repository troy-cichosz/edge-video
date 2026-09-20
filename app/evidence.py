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

def build_manifest(config, camera, video_path: Path, started_at, ended_at=None, started_monotonic_ns=None, edge_time_context=None):
    ended_at = ended_at or utc_now()
    stat = video_path.stat()
    capture = {
        "start_utc": started_at.isoformat().replace("+00:00", "Z"),
        "end_utc": ended_at.isoformat().replace("+00:00", "Z"),
        "start_monotonic_ns": started_monotonic_ns or time.monotonic_ns(),
        "clock_source": "system",
        "time_quality": "unsynchronized",
        "gps_authority": False,
    }
    manifest = {
        "schema": "ai-legal.evidence.video.v1",
        "evidence_id": evidence_id(),
        "service": config.service_id,
        "service_version": config.service_version,
        "node_id": config.node_id,
        "capture": capture,
        "camera": camera,
        "video": {"filename": video_path.name, "bytes": stat.st_size, "sha256": sha256_file(video_path), "format": "h264", "codec": "h264", "width": config.width, "height": config.height, "framerate": config.framerate, "bitrate": config.bitrate},
        "integrity": {"hash_algorithm": "SHA-256", "payload_immutable": True, "manifest_immutable": True},
        "gps": None,
        "notes": ["Video is stored as segmented H.264 elementary streams in this release."],
    }
    if edge_time_context is not None:
        manifest["temporal_provenance"] = {
            "context_acquisition": "edge-time Capture Time Context acquired near segment creation",
            "capture_time_semantics": "context_acquisition_not_physical_exposure",
            "edge_time": edge_time_context,
        }
        capture["clock_source"] = "edge-time-context"
        capture["time_quality"] = edge_time_context.get("synchronization_state", "unknown")
    else:
        manifest["temporal_provenance"] = {
            "context_acquisition": None,
            "capture_time_semantics": "system_start_time_only",
            "edge_time": None,
        }
        manifest["notes"].append("Node-local edge-time context was unavailable near segment creation.")
    return manifest


def build_evidence_envelope(manifest: dict) -> dict:
    """Build the Round 1 common evidence envelope from the video manifest."""
    capture = manifest["capture"]
    return {
        "schema": "ai-legal.evidence.envelope.v1",
        "evidence_id": manifest["evidence_id"],
        "service": manifest["service"],
        "service_version": manifest["service_version"],
        "node_id": manifest["node_id"],
        "source": {},
        "capture": {
            "start": capture["start_utc"],
            "end": None,
            "monotonic_start_ns": capture.get("start_monotonic_ns"),
            "time_semantics": "service_start_reference; segment_physical_interval_not_established",
        },
        "time_context": manifest.get("temporal_provenance", {}).get("edge_time"),
        "artifacts": [
            {
                "artifact_id": f'{manifest["evidence_id"]}:video',
                "role": "authoritative",
                "filename": manifest["video"]["filename"],
                "media_type": "video/h264",
                "size": manifest["video"]["bytes"],
                "sha256": manifest["video"]["sha256"],
            }
        ],
        "configuration": None,
        "derivation": None,
        "service_metadata": {
            "camera": manifest["camera"],
            "video": manifest["video"],
            "media_pipeline": manifest.get("media_pipeline"),
            "integrity": manifest["integrity"],
        },
    }
