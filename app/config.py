import os
import socket
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    controller_url: str
    controller_timeout: int
    node_id: str
    service_id: str
    service_name: str
    service_version: str

    camera_index: int
    width: int
    height: int
    framerate: int
    bitrate: int
    segment_seconds: int
    inline_headers: bool

    evidence_root: Path

    live_root: Path
    hls_segment_seconds: int
    hls_segment_count: int
    enable_stream: bool

    rpicam_bin: str
    ffmpeg_bin: str

    health_host: str
    health_port: int


def load_config() -> Config:
    return Config(
        controller_url=os.getenv(
            "EDGE_CONTROLLER_URL",
            "",
        ).rstrip("/"),

        controller_timeout=int(
            os.getenv("EDGE_CONTROLLER_TIMEOUT", "5")
        ),

        node_id=os.getenv(
            "EDGE_NODE_ID",
            socket.gethostname(),
        ),

        service_id=os.getenv(
            "EDGE_SERVICE_ID",
            "edge-video",
        ),

        service_name=os.getenv(
            "EDGE_SERVICE_NAME",
            "edge-video",
        ),

        service_version=os.getenv(
            "EDGE_SERVICE_VERSION",
            "0.1.0",
        ),

        camera_index=int(
            os.getenv("EDGE_VIDEO_CAMERA_INDEX", "0")
        ),

        width=int(
            os.getenv("EDGE_VIDEO_WIDTH", "1920")
        ),

        height=int(
            os.getenv("EDGE_VIDEO_HEIGHT", "1080")
        ),

        framerate=int(
            os.getenv("EDGE_VIDEO_FRAMERATE", "30")
        ),

        bitrate=int(
            os.getenv("EDGE_VIDEO_BITRATE", "12000000")
        ),

        segment_seconds=int(
            os.getenv("EDGE_VIDEO_SEGMENT_SECONDS", "60")
        ),

        inline_headers=_bool(
            "EDGE_VIDEO_INLINE_HEADERS",
            True,
        ),

        evidence_root=Path(
            os.getenv(
                "EDGE_VIDEO_EVIDENCE_ROOT",
                "/recordings",
            )
        ),

        enable_stream=_bool(
            "EDGE_VIDEO_ENABLE_STREAM",
            False,
        ),

        live_root=Path(
            os.getenv(
                "EDGE_VIDEO_LIVE_ROOT",
                "/tmp/edge-video-live",
            )
        ),

        hls_segment_seconds=int(
            os.getenv(
                "EDGE_VIDEO_HLS_SEGMENT_SECONDS",
                "1",
            )
        ),

        hls_segment_count=int(
            os.getenv(
                "EDGE_VIDEO_HLS_SEGMENT_COUNT",
                "3"
            )
        ),

        rpicam_bin=os.getenv(
            "EDGE_VIDEO_RPICAM_BIN",
            "rpicam-vid",
        ),

        ffmpeg_bin=os.getenv(
            "EDGE_VIDEO_FFMPEG_BIN",
            "ffmpeg",
        ),

        health_host=os.getenv(
            "EDGE_VIDEO_HEALTH_HOST",
            "0.0.0.0",
        ),

        health_port=int(
            os.getenv("EDGE_VIDEO_HEALTH_PORT", "8090")
        ),
    )