import logging
import threading
import time
from datetime import datetime, timezone

from .evidence import (
    build_manifest,
    fsync_file,
    write_json_atomic,
)

logger = logging.getLogger(__name__)


class Recorder:
    """
    Finalizes evidence segments produced by the media pipeline.

    This class deliberately does not open the camera. MediaPipeline owns the
    single rpicam process.
    """

    def __init__(self, config, camera_info, media):
        self.config = config
        self.camera_info = camera_info
        self.media = media

        self.root = config.evidence_root
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.manifest_dir = self.root / "manifests"
        self.manifest_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._stop = threading.Event()
        self._watcher = None
        self._known = set()

        self.started_at = None
        self.started_monotonic_ns = None

    @property
    def process(self):
        """
        Compatibility property used by main.py.

        The camera process is owned by MediaPipeline.
        """
        return self.media.capture_process

    def start(self):
        self.started_at = datetime.now(timezone.utc)
        self.started_monotonic_ns = time.monotonic_ns()

        self.media.start()

        self._watcher = threading.Thread(
            target=self._watch_segments,
            name="edge-video-evidence-finalizer",
            daemon=True,
        )
        self._watcher.start()

        logger.info(
            "Evidence recorder started"
        )

    def stop(self):
        self._stop.set()

        self.media.stop()

        if self._watcher:
            self._watcher.join(timeout=5)

        # Give the final segment a chance to settle after FFmpeg closes.
        self._finalize_remaining()

    def _watch_segments(self):
        while not self._stop.wait(2):
            self._finalize_available()

    def _finalize_available(self):
        for path in sorted(
            self.root.glob("segment*.h264")
        ):
            if path.name in self._known:
                continue

            if not self._is_stable(path):
                continue

            try:
                self._finalize(path)
                self._known.add(path.name)

            except Exception:
                logger.exception(
                    "Failed to finalize evidence segment %s",
                    path.name,
                )

    def _finalize_remaining(self):
        for _ in range(5):
            self._finalize_available()

            time.sleep(0.25)

    @staticmethod
    def _is_stable(path):
        try:
            first = path.stat().st_size

            time.sleep(0.25)

            second = path.stat().st_size

            return (
                first == second
                and second > 0
            )

        except FileNotFoundError:
            return False

    def _finalize(self, path):
        fsync_file(path)

        manifest = build_manifest(
            self.config,
            self.camera_info,
            path,
            self.started_at,
        )

        manifest["capture"]["service_start_monotonic_ns"] = (
            self.started_monotonic_ns
        )

        manifest["capture"]["segment_timing"] = (
            "ffmpeg_segment_muxer_keyframe_aligned; "
            "raw_h264_has_no_embedded_container_timestamps"
        )

        manifest["media_pipeline"] = {
            "camera_owner": "rpicam-vid",
            "encoded_format": "h264",
            "evidence_transport": "stdout->ffmpeg",
            "live_transport": (
                "stdout->ffmpeg->hls"
                if self.config.enable_stream
                else None
            ),
        }

        manifest_path = (
            self.manifest_dir
            / f"{path.stem}.json"
        )

        write_json_atomic(
            manifest_path,
            manifest,
        )

        logger.info(
            "Evidence finalized: %s sha256=%s",
            path.name,
            manifest["video"]["sha256"],
        )